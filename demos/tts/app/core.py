"""Text handling, RunPod calls and wav assembly for the text to speech demo."""

from __future__ import annotations

import io
import os
import re
import wave
from dataclasses import dataclass
from pathlib import Path

import httpx

# The 20 preset voice ids documented for the RunPod chatterbox-turbo endpoint,
# in the order the docs list them.
VOICES: tuple[str, ...] = (
    "aaron",
    "abigail",
    "anaya",
    "andy",
    "archer",
    "brian",
    "chloe",
    "dylan",
    "emmanuel",
    "ethan",
    "evelyn",
    "gavin",
    "gordon",
    "ivan",
    "laura",
    "lucy",
    "madison",
    "marisol",
    "meera",
    "walter",
)
DEFAULT_VOICE = "lucy"
AUDIO_FORMAT = "wav"
RUNPOD_BASE_URL = "https://api.runpod.ai/v2"
PREVIEW_SENTENCE = "This is my voice reading a line of text so you can hear how it sounds."
# Chunks stay at or below this many characters so each RunPod call is short.
CHUNK_TARGET_CHARS = 600
# A sentence is only split further once a chunk would otherwise pass the target.
CHUNK_MIN_CHARS = 400
CLONE_MAX_BYTES = 5 * 1024 * 1024
CLONE_MAX_SECONDS = 30.0
CLONE_EXTENSIONS = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".ogg": "audio/ogg"}
_SENTENCE_END = re.compile(r"(?<=[.!?…])[\"')\]]*\s+|(?<=[.!?…][\"')\]])\s+")


class UpstreamError(Exception):
    """A RunPod call failed. The message is already redacted and user facing."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


class AudioMismatch(Exception):
    """Two chunk files disagree on sample rate, channel count or sample width."""


@dataclass(frozen=True)
class ChunkAudio:
    index: int
    path: Path
    seconds: float


def api_key() -> str:
    return os.getenv("RUNPOD_API_KEY", "").strip()


def endpoint() -> str:
    return os.getenv("TTS_ENDPOINT", "chatterbox-turbo").strip() or "chatterbox-turbo"


def endpoint_url() -> str:
    target = endpoint()
    if "://" in target:
        return target.rstrip("/") + "/runsync"
    return f"{RUNPOD_BASE_URL}/{target}/runsync"


def max_words() -> int:
    try:
        value = int(os.getenv("MAX_WORDS", "2000"))
    except ValueError:
        return 2000
    return value if value > 0 else 2000


def data_dir() -> Path:
    return Path(os.getenv("DATA_DIR", "/data"))


def public_base_url() -> str:
    return os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")


def cloning_enabled() -> bool:
    return bool(public_base_url())


def count_words(text: str) -> int:
    return len(text.split())


def redact(text: str) -> str:
    """Remove the API key from anything that reaches a user or a log line."""
    key = api_key()
    cleaned = " ".join(str(text).split())
    if key:
        cleaned = cleaned.replace(key, "[redacted]")
        tail = key[-8:]
        if len(tail) >= 8:
            cleaned = cleaned.replace(tail, "[redacted]")
    return cleaned


def _split_long_sentence(sentence: str, limit: int) -> list[str]:
    """Break one oversized sentence on whitespace so no word is cut in half."""
    pieces: list[str] = []
    current = ""
    for word in sentence.split():
        if not current:
            current = word
            continue
        if len(current) + 1 + len(word) <= limit:
            current = f"{current} {word}"
        else:
            pieces.append(current)
            current = word
    if current:
        pieces.append(current)
    return pieces


def chunk_text(text: str, limit: int = CHUNK_TARGET_CHARS) -> list[str]:
    """Split text at paragraph then sentence boundaries into pieces under the limit."""
    chunks: list[str] = []
    current = ""
    for paragraph in re.split(r"\n\s*\n+", text.strip()):
        paragraph = " ".join(paragraph.split())
        if not paragraph:
            continue
        for sentence in _SENTENCE_END.split(paragraph):
            sentence = sentence.strip()
            if not sentence:
                continue
            for piece in (
                [sentence] if len(sentence) <= limit else _split_long_sentence(sentence, limit)
            ):
                if not current:
                    current = piece
                elif len(current) + 1 + len(piece) <= limit:
                    current = f"{current} {piece}"
                else:
                    chunks.append(current)
                    current = piece
        if current and len(current) >= CHUNK_MIN_CHARS:
            chunks.append(current)
            current = ""
    if current:
        chunks.append(current)
    return chunks


def _upstream_message(status: int, body: str) -> str:
    detail = redact(body)[:400]
    if status == 401:
        return f"RunPod rejected the API key with a 401. Check RUNPOD_API_KEY. Upstream said: {detail}"
    if status == 402:
        return f"The RunPod account has no credit, so it answered 402. Add credit and try again. Upstream said: {detail}"
    return f"RunPod answered {status}. Upstream said: {detail}"


async def synthesize(
    client: httpx.AsyncClient,
    text: str,
    voice: str = DEFAULT_VOICE,
    voice_url: str | None = None,
) -> bytes:
    """Send one chunk to RunPod and return the wav bytes it produced."""
    key = api_key()
    if not key:
        raise UpstreamError("RUNPOD_API_KEY is not set, so the app cannot call RunPod.")
    payload: dict[str, object] = {"prompt": text, "format": AUDIO_FORMAT}
    if voice_url:
        payload["voice_url"] = voice_url
    else:
        payload["voice"] = voice
    try:
        response = await client.post(
            endpoint_url(),
            json={"input": payload},
            headers={"Authorization": f"Bearer {key}"},
        )
    except httpx.HTTPError as error:
        raise UpstreamError(f"The RunPod request failed: {redact(repr(error))}") from None
    if response.status_code != 200:
        raise UpstreamError(
            _upstream_message(response.status_code, response.text), response.status_code
        )
    try:
        body = response.json()
    except ValueError:
        raise UpstreamError(f"RunPod returned a body that is not JSON: {redact(response.text)[:400]}") from None
    status = str(body.get("status", "")).upper()
    if status != "COMPLETED":
        detail = redact(body.get("error") or body.get("output") or body)[:400]
        raise UpstreamError(f"RunPod reported status {status or 'unknown'}. Upstream said: {detail}")
    audio_url = (body.get("output") or {}).get("audio_url")
    if not audio_url:
        raise UpstreamError(f"RunPod returned no audio_url. Upstream said: {redact(body)[:400]}")
    try:
        audio = await client.get(audio_url)
    except httpx.HTTPError as error:
        raise UpstreamError(f"Downloading the audio failed: {redact(repr(error))}") from None
    if audio.status_code != 200:
        raise UpstreamError(
            f"Downloading the audio from RunPod answered {audio.status_code}.", audio.status_code
        )
    return audio.content


def wav_seconds(data: bytes) -> float:
    with wave.open(io.BytesIO(data), "rb") as handle:
        return handle.getnframes() / float(handle.getframerate())


def write_chunk(path: Path, data: bytes) -> float:
    """Store one chunk's wav on disk and return its duration in seconds."""
    seconds = wav_seconds(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return seconds


def concat_wavs(paths: list[Path], target: Path) -> float:
    """Join chunk wav files in order into one wav and return its duration."""
    if not paths:
        raise AudioMismatch("There is no audio to join.")
    target.parent.mkdir(parents=True, exist_ok=True)
    shape: tuple[int, int, int] | None = None
    frames = 0
    with wave.open(str(target), "wb") as out:
        for path in paths:
            with wave.open(str(path), "rb") as part:
                current = (part.getnchannels(), part.getsampwidth(), part.getframerate())
                if shape is None:
                    shape = current
                    out.setnchannels(current[0])
                    out.setsampwidth(current[1])
                    out.setframerate(current[2])
                elif current != shape:
                    raise AudioMismatch(
                        f"{path.name} is {current[2]} Hz with {current[0]} channel(s) "
                        f"and the run started at {shape[2]} Hz with {shape[0]} channel(s)."
                    )
                data = part.readframes(part.getnframes())
                frames += part.getnframes()
                out.writeframes(data)
    assert shape is not None
    return frames / float(shape[2])
