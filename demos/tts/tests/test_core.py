from __future__ import annotations

import io
import wave

import pytest

from app import core
from tests.conftest import make_wav

DOCUMENTED_VOICES = [
    "aaron", "abigail", "anaya", "andy", "archer", "brian", "chloe", "dylan",
    "emmanuel", "ethan", "evelyn", "gavin", "gordon", "ivan", "laura", "lucy",
    "madison", "marisol", "meera", "walter",
]


def test_voice_list_matches_the_runpod_docs():
    assert list(core.VOICES) == DOCUMENTED_VOICES
    assert len(core.VOICES) == 20
    assert core.DEFAULT_VOICE == "lucy"


def test_count_words_uses_whitespace_after_trimming():
    assert core.count_words("  one   two\nthree\t four  ") == 4
    assert core.count_words("   ") == 0


def test_endpoint_url_takes_a_slug_or_a_full_base_url(monkeypatch):
    monkeypatch.delenv("TTS_ENDPOINT", raising=False)
    assert core.endpoint_url() == "https://api.runpod.ai/v2/chatterbox-turbo/runsync"
    monkeypatch.setenv("TTS_ENDPOINT", "http://127.0.0.1:9000/v2/chatterbox-turbo")
    assert core.endpoint_url() == "http://127.0.0.1:9000/v2/chatterbox-turbo/runsync"


def test_cloning_is_off_until_public_base_url_is_set(monkeypatch):
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    assert core.cloning_enabled() is False
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://runpoddemo1.galaxygate.app")
    assert core.cloning_enabled() is True


def test_redact_removes_the_key(monkeypatch):
    monkeypatch.setenv("RUNPOD_API_KEY", "rpa_SECRET_0123456789")
    message = core.redact("401 for token rpa_SECRET_0123456789 sent by the app")
    assert "rpa_SECRET_0123456789" not in message
    assert "[redacted]" in message


LONG_TEXT = (
    "Philadelphia sits at the confluence of the Delaware and the Schuylkill. "
    "The grid William Penn drew still holds the centre of the city together. "
    "Market Street runs east to west and Broad Street runs north to south. "
    "Every hackathon needs a demo that speaks for itself, so this one reads text aloud.\n\n"
    "The model is open, which matters because the weights can be inspected and hosted anywhere. "
    "RunPod serves it behind a public endpoint with no cold start, and the app chunks long text. "
    "Each chunk is generated in order and streamed back as soon as it is ready. "
    "That is why the first sentence plays while the last one is still being made. "
    "A single wav file is joined at the end so the whole reading can be downloaded."
)


def test_chunks_stay_under_the_target_and_never_split_a_word():
    chunks = core.chunk_text(LONG_TEXT)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= core.CHUNK_TARGET_CHARS
    original = LONG_TEXT.split()
    rejoined = " ".join(chunks).split()
    assert rejoined == original


def test_an_oversized_sentence_is_split_on_whitespace():
    sentence = " ".join(["Schuylkill"] * 200) + "."
    chunks = core.chunk_text(sentence)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= core.CHUNK_TARGET_CHARS
    assert " ".join(chunks).split() == sentence.split()
    for chunk in chunks:
        for word in chunk.split():
            assert word in {"Schuylkill", "Schuylkill."}


def test_paragraph_boundaries_are_preferred_once_a_chunk_is_big_enough():
    paragraph = " ".join(["Sentence number one here."] * 20)
    chunks = core.chunk_text(f"{paragraph}\n\n{paragraph}")
    assert all(len(chunk) <= core.CHUNK_TARGET_CHARS for chunk in chunks)
    assert all(len(chunk) >= core.CHUNK_MIN_CHARS for chunk in chunks[:-1])


def test_concat_wavs_keeps_the_header_and_sums_the_duration(tmp_path):
    parts = []
    for index, amplitude in enumerate((1000, 2000, 3000)):
        path = tmp_path / f"{index:03d}.wav"
        path.write_bytes(make_wav(amplitude, frames=1200))
        parts.append(path)
    target = tmp_path / "full.wav"
    seconds = core.concat_wavs(parts, target)
    with wave.open(str(target), "rb") as handle:
        assert handle.getnchannels() == 1
        assert handle.getsampwidth() == 2
        assert handle.getframerate() == 24000
        assert handle.getnframes() == 3600
        frames = handle.readframes(handle.getnframes())
    assert seconds == pytest.approx(3600 / 24000)
    assert target.read_bytes()[:4] == b"RIFF"
    order = [
        int.from_bytes(frames[offset * 2400 : offset * 2400 + 2], "little", signed=True)
        for offset in range(3)
    ]
    assert order == [1000, 2000, 3000]


def test_concat_wavs_refuses_mismatched_audio(tmp_path):
    first = tmp_path / "000.wav"
    first.write_bytes(make_wav(1000))
    second = tmp_path / "001.wav"
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00" * 400)
    second.write_bytes(buffer.getvalue())
    with pytest.raises(core.AudioMismatch):
        core.concat_wavs([first, second], tmp_path / "full.wav")
