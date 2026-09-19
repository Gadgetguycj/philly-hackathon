"""FastAPI app: paste text, pick a voice, hear it as the chunks arrive."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import httpx
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from tinytag import TinyTag, TinyTagException

from .core import (
    AUDIO_FORMAT,
    CLONE_EXTENSIONS,
    CLONE_MAX_BYTES,
    CLONE_MAX_SECONDS,
    DEFAULT_VOICE,
    PREVIEW_SENTENCE,
    VOICES,
    AudioMismatch,
    UpstreamError,
    api_key,
    chunk_text,
    cloning_enabled,
    concat_wavs,
    count_words,
    data_dir,
    endpoint,
    max_words,
    public_base_url,
    redact,
    synthesize,
    write_chunk,
)

APP_DIR = Path(__file__).parent
STATIC_DIR = APP_DIR / "static"
ID_PATTERN = re.compile(r"^[0-9a-f]{12}$")
CHUNK_PATTERN = re.compile(r"^[0-9]{3}$")
HEARTBEAT_SECONDS = 10.0
CHUNK_TIMEOUT_SECONDS = 600.0
STREAM_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        ensure_data_dir()
        if not os.access(data_dir(), os.W_OK | os.X_OK):
            raise PermissionError(data_dir())
    except OSError:
        logger.error(
            "DATA_DIR %s is not writable; create the host directory with "
            "install -d -o 1000 -g 1000 %s",
            data_dir(),
            data_dir(),
        )
        raise SystemExit(1) from None
    yield


app = FastAPI(title="Text to Speech", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def runs_dir() -> Path:
    return data_dir() / "runs"


def previews_dir() -> Path:
    return data_dir() / "previews"


def clones_dir() -> Path:
    return data_dir() / "clones"


def ensure_data_dir() -> None:
    for path in (runs_dir(), previews_dir(), clones_dir()):
        path.mkdir(parents=True, exist_ok=True)


def new_client() -> httpx.AsyncClient:
    timeout = httpx.Timeout(CHUNK_TIMEOUT_SECONDS, connect=20.0)
    return httpx.AsyncClient(timeout=timeout, follow_redirects=True)


def sse(event: dict) -> bytes:
    return f"data: {json.dumps(event)}\n\n".encode()


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "runpod_key_set": bool(api_key()),
            "endpoint": endpoint(),
            "max_words": max_words(),
            "cloning_enabled": cloning_enabled(),
        }
    )


@app.get("/api/voices")
def voices() -> JSONResponse:
    return JSONResponse(
        {
            "voices": list(VOICES),
            "default": DEFAULT_VOICE,
            "preview_sentence": PREVIEW_SENTENCE,
            "max_words": max_words(),
            "cloning_enabled": cloning_enabled(),
            "clone_max_seconds": CLONE_MAX_SECONDS,
            "clone_max_bytes": CLONE_MAX_BYTES,
            "clone_extensions": sorted(CLONE_EXTENSIONS),
        }
    )


def clone_path(clone_id: str) -> Path | None:
    if not ID_PATTERN.match(clone_id):
        return None
    for extension in CLONE_EXTENSIONS:
        candidate = clones_dir() / f"{clone_id}{extension}"
        if candidate.exists():
            return candidate
    return None


@app.post("/api/clone")
async def upload_clone(clip: UploadFile = File(...)) -> JSONResponse:
    if not cloning_enabled():
        raise HTTPException(
            400,
            "Voice cloning is off because PUBLIC_BASE_URL is not set. RunPod has to fetch "
            "the clip over the internet, so the app needs to know its own public address.",
        )
    extension = Path(clip.filename or "").suffix.lower()
    if extension not in CLONE_EXTENSIONS:
        raise HTTPException(
            400,
            f"{extension or 'that file type'} is not accepted. Upload a "
            f"{', '.join(sorted(CLONE_EXTENSIONS))} file.",
        )
    data = await clip.read(CLONE_MAX_BYTES + 1)
    if len(data) > CLONE_MAX_BYTES:
        raise HTTPException(
            400, f"The clip is over the {CLONE_MAX_BYTES // (1024 * 1024)} MB limit."
        )
    if not data:
        raise HTTPException(400, "The clip is empty.")
    ensure_data_dir()
    clone_id = secrets.token_hex(6)
    target = clones_dir() / f"{clone_id}{extension}"
    target.write_bytes(data)
    try:
        seconds = TinyTag.get(target).duration
    except (TinyTagException, ValueError, OSError):
        seconds = None
    if seconds is None:
        target.unlink(missing_ok=True)
        raise HTTPException(
            400, "The clip's length could not be read, so it was rejected. Try a wav file."
        )
    if seconds > CLONE_MAX_SECONDS:
        target.unlink(missing_ok=True)
        raise HTTPException(
            400,
            f"The clip is {seconds:.1f} seconds and the limit is "
            f"{CLONE_MAX_SECONDS:.0f} seconds.",
        )
    return JSONResponse(
        {
            "clone_id": clone_id,
            "url": f"{public_base_url()}/clones/{target.name}",
            "seconds": round(seconds, 2),
        }
    )


@app.get("/clones/{name}")
def clone_file(name: str) -> FileResponse:
    candidate = clones_dir() / name
    if Path(name).name != name or not candidate.is_file():
        raise HTTPException(404, "That clip is not here.")
    media_type = CLONE_EXTENSIONS.get(candidate.suffix.lower(), "application/octet-stream")
    return FileResponse(candidate, media_type=media_type)


@app.get("/p/{voice}.wav")
async def preview(voice: str) -> FileResponse:
    if voice not in VOICES:
        raise HTTPException(404, f"{voice} is not one of the {len(VOICES)} preset voices.")
    ensure_data_dir()
    target = previews_dir() / f"{voice}.{AUDIO_FORMAT}"
    if not target.exists():
        async with new_client() as client:
            try:
                audio = await synthesize(client, PREVIEW_SENTENCE, voice=voice)
            except UpstreamError as error:
                raise HTTPException(502, error.message) from None
        try:
            write_chunk(target, audio)
        except Exception as error:
            target.unlink(missing_ok=True)
            raise HTTPException(502, f"RunPod returned audio this app cannot read: {redact(error)}") from None
    return FileResponse(target, media_type="audio/wav")


@app.get("/a/{run_id}.wav")
def full_audio(run_id: str) -> FileResponse:
    if not ID_PATTERN.match(run_id):
        raise HTTPException(404, "That is not a run id.")
    target = runs_dir() / run_id / f"full.{AUDIO_FORMAT}"
    if not target.is_file():
        raise HTTPException(404, "That run has no finished audio.")
    return FileResponse(
        target,
        media_type="audio/wav",
        headers={"Content-Disposition": f'attachment; filename="speech-{run_id}.wav"'},
    )


@app.get("/a/{run_id}/{index}.wav")
def chunk_audio(run_id: str, index: str) -> FileResponse:
    if not ID_PATTERN.match(run_id) or not CHUNK_PATTERN.match(index):
        raise HTTPException(404, "That is not a chunk.")
    target = runs_dir() / run_id / f"{index}.{AUDIO_FORMAT}"
    if not target.is_file():
        raise HTTPException(404, "That chunk is not here.")
    return FileResponse(target, media_type="audio/wav")


async def speak_stream(chunks: list[str], voice: str, voice_url: str | None, run_id: str) -> AsyncIterator[bytes]:
    run_path = runs_dir() / run_id
    run_path.mkdir(parents=True, exist_ok=True)
    yield sse({"type": "start", "id": run_id, "chunks": len(chunks), "voice": voice})
    written: list[Path] = []
    async with new_client() as client:
        for index, text in enumerate(chunks):
            task = asyncio.create_task(synthesize(client, text, voice=voice, voice_url=voice_url))
            try:
                while True:
                    done, _ = await asyncio.wait({task}, timeout=HEARTBEAT_SECONDS)
                    if done:
                        break
                    yield sse({"type": "ping", "index": index})
            finally:
                # The browser can close the tab mid chunk, which closes this generator.
                if not task.done():
                    task.cancel()
            try:
                audio = task.result()
                target = run_path / f"{index:03d}.{AUDIO_FORMAT}"
                seconds = write_chunk(target, audio)
            except UpstreamError as error:
                yield sse({"type": "error", "message": error.message})
                return
            except Exception as error:
                yield sse(
                    {
                        "type": "error",
                        "message": f"Chunk {index + 1} came back as audio this app cannot read: {redact(error)}",
                    }
                )
                return
            written.append(target)
            yield sse(
                {
                    "type": "chunk",
                    "index": index,
                    "url": f"/a/{run_id}/{index:03d}.wav",
                    "seconds": round(seconds, 2),
                    "characters": len(text),
                }
            )
    try:
        total = concat_wavs(written, run_path / f"full.{AUDIO_FORMAT}")
    except AudioMismatch as error:
        yield sse({"type": "error", "message": f"The chunks could not be joined: {redact(error)}"})
        return
    yield sse(
        {
            "type": "done",
            "id": run_id,
            "url": f"/a/{run_id}.wav",
            "chunks": len(written),
            "seconds": round(total, 2),
        }
    )


@app.post("/api/speak")
async def speak(request: Request) -> StreamingResponse:
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(400, "The request body is not JSON.") from None
    text = str(body.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "There is no text to speak.")
    limit = max_words()
    words = count_words(text)
    if words > limit:
        extra = words - limit
        raise HTTPException(
            400,
            f"That is {words} words and the cap is {limit} words per run. "
            f"Remove {extra} {'word' if extra == 1 else 'words'} and press Speak again.",
        )
    voice = str(body.get("voice") or DEFAULT_VOICE).strip()
    if voice not in VOICES:
        raise HTTPException(400, f"{voice} is not one of the {len(VOICES)} preset voices.")
    voice_url = None
    clone_id = str(body.get("clone_id") or "").strip()
    if clone_id:
        if not cloning_enabled():
            raise HTTPException(
                400,
                "Voice cloning is off because PUBLIC_BASE_URL is not set.",
            )
        stored = clone_path(clone_id)
        if stored is None:
            raise HTTPException(400, "That uploaded clip is gone. Upload it again.")
        voice_url = f"{public_base_url()}/clones/{stored.name}"
    if not api_key():
        raise HTTPException(500, "RUNPOD_API_KEY is not set, so the app cannot call RunPod.")
    chunks = chunk_text(text)
    if not chunks:
        raise HTTPException(400, "There is no text to speak.")
    ensure_data_dir()
    run_id = secrets.token_hex(6)
    return StreamingResponse(
        speak_stream(chunks, voice, voice_url, run_id),
        media_type="text/event-stream",
        headers=STREAM_HEADERS,
    )
