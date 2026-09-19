from __future__ import annotations

import io
import json
import logging
import time
import wave
from pathlib import Path

import httpx
import pytest

from app import core
from tests.conftest import TEST_KEY, CHUNK_FRAMES, FRAMERATE, marker_for

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "two-paragraphs.txt"
TWO_PARAGRAPHS = SAMPLE.read_text(encoding="utf-8")


def events_from(response) -> list[dict]:
    collected = []
    for line in response.iter_lines():
        if line.startswith("data: "):
            collected.append(json.loads(line[6:]))
    return collected


def run_speak(test_client, text, **body):
    with test_client.stream("POST", "/api/speak", json={"text": text, **body}) as response:
        assert response.status_code == 200, response.read()
        return events_from(response)


def test_health_reports_the_configuration(configure, client):
    configure()
    response = client().get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "status": "ok",
        "runpod_key_set": True,
        "endpoint": "chatterbox-turbo",
        "max_words": 2000,
        "cloning_enabled": False,
    }
    assert TEST_KEY not in response.text


def test_voices_endpoint_lists_all_twenty_presets(configure, client):
    configure()
    body = client().get("/api/voices").json()
    assert body["voices"] == list(core.VOICES)
    assert len(body["voices"]) == 20
    assert body["default"] == "lucy"
    assert body["cloning_enabled"] is False


def test_the_word_cap_rejects_2001_words_before_calling_runpod(upstream, configure, client):
    configure(upstream)
    text = " ".join(["word"] * 2001)
    response = client().post("/api/speak", json={"text": text, "voice": "lucy"})
    assert response.status_code == 400
    assert "2001 words" in response.json()["detail"]
    assert "cap is 2000 words" in response.json()["detail"]
    assert "Remove 1 word and" in response.json()["detail"]
    assert upstream.requests == []


def test_the_word_cap_lets_1999_words_through(upstream, configure, client):
    configure(upstream)
    text = " ".join(["word"] * 1999)
    events = run_speak(client(), text)
    assert events[0]["type"] == "start"
    assert events[-1]["type"] == "done"
    assert len(upstream.requests) == events[0]["chunks"]


def test_chunk_order_is_preserved_in_the_assembled_file(upstream, configure, client):
    configure(upstream)
    test_client = client()
    events = run_speak(test_client, TWO_PARAGRAPHS)
    done = events[-1]
    assert done["type"] == "done"
    chunks = core.chunk_text(TWO_PARAGRAPHS)
    assert len(chunks) > 2
    assert upstream.prompts() == chunks
    expected = [marker_for(chunk) for chunk in chunks]
    assert len(set(expected)) == len(expected)
    audio = test_client.get(done["url"])
    assert audio.status_code == 200
    with wave.open(str(core.data_dir() / "runs" / done["id"] / "full.wav"), "rb") as handle:
        frames = handle.readframes(handle.getnframes())
    stride = CHUNK_FRAMES * 2
    found = [
        int.from_bytes(frames[index * stride : index * stride + 2], "little", signed=True)
        for index in range(len(chunks))
    ]
    assert found == expected


def test_the_assembled_wav_has_the_right_header_and_total_duration(upstream, configure, client):
    configure(upstream)
    test_client = client()
    events = run_speak(test_client, TWO_PARAGRAPHS)
    parts = [event for event in events if event["type"] == "chunk"]
    done = events[-1]
    assert [part["index"] for part in parts] == list(range(len(parts)))
    body = test_client.get(done["url"]).content
    assert body[:4] == b"RIFF"
    assert body[8:12] == b"WAVE"
    path = core.data_dir() / "runs" / done["id"] / "full.wav"
    with wave.open(str(path), "rb") as handle:
        assert handle.getnchannels() == 1
        assert handle.getsampwidth() == 2
        assert handle.getframerate() == FRAMERATE
        assert handle.getnframes() == CHUNK_FRAMES * len(parts)
    assert done["seconds"] == pytest.approx(sum(part["seconds"] for part in parts), abs=0.01)


def test_the_first_chunk_is_playable_before_the_last_one_is_requested(
    upstream, configure, live_server
):
    """The proof of streaming: fetch chunk one and play it while later chunks are pending."""
    configure(upstream)
    upstream.delay = 0.4
    base = live_server()
    chunks = core.chunk_text(TWO_PARAGRAPHS)
    assert len(chunks) >= 3
    first_chunk_at = None
    first_chunk_bytes = b""
    requests_when_first_landed = 0
    with httpx.Client(base_url=base, timeout=60.0) as browser:
        with browser.stream("POST", "/api/speak", json={"text": TWO_PARAGRAPHS}) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            for line in response.iter_lines():
                if not line.startswith("data: "):
                    continue
                event = json.loads(line[6:])
                if event["type"] == "chunk" and first_chunk_at is None:
                    first_chunk_at = time.monotonic()
                    requests_when_first_landed = len(upstream.requests)
                    first_chunk_bytes = browser.get(event["url"]).content
    last_request_at = max(item["at"] for item in upstream.requests)
    assert first_chunk_at is not None
    assert len(upstream.requests) == len(chunks)
    assert requests_when_first_landed < len(chunks)
    assert first_chunk_at < last_request_at
    assert first_chunk_bytes[:4] == b"RIFF"
    assert first_chunk_bytes[8:12] == b"WAVE"
    with wave.open(io.BytesIO(first_chunk_bytes), "rb") as handle:
        assert handle.getnframes() == CHUNK_FRAMES


def test_the_stream_sends_a_heartbeat_while_a_chunk_is_slow(upstream, configure, client, monkeypatch):
    monkeypatch.setattr("app.main.HEARTBEAT_SECONDS", 0.1)
    configure(upstream)
    upstream.delay = 0.45
    events = run_speak(client(), "One short line for the heartbeat test.")
    assert any(event["type"] == "ping" for event in events)
    assert events[-1]["type"] == "done"


def test_the_api_key_never_appears_in_a_response_or_a_log_line(
    upstream, configure, client, caplog
):
    configure(upstream)
    upstream.status = 500
    with caplog.at_level(logging.DEBUG):
        events = run_speak(client(), TWO_PARAGRAPHS)
        health = client().get("/health").text
        voices = client().get("/api/voices").text
    failure = [event for event in events if event["type"] == "error"]
    assert failure, events
    assert upstream.requests[0]["authorization"] == f"Bearer {TEST_KEY}"
    assert "[redacted]" in failure[0]["message"]
    serialised = json.dumps(events)
    assert TEST_KEY not in serialised
    assert TEST_KEY not in health
    assert TEST_KEY not in voices
    for record in caplog.records:
        assert TEST_KEY not in record.getMessage()


def test_a_402_from_runpod_becomes_a_credit_message(upstream, configure, client):
    configure(upstream)
    upstream.status = 402
    upstream.body = '{"error":"insufficient funds"}'
    events = run_speak(client(), "A single short line of text.")
    failure = events[-1]
    assert failure["type"] == "error"
    assert "no credit" in failure["message"]
    assert "402" in failure["message"]
    assert "insufficient funds" in failure["message"]


def test_a_401_from_runpod_names_the_key(upstream, configure, client):
    configure(upstream)
    upstream.status = 401
    events = run_speak(client(), "A single short line of text.")
    assert events[-1]["type"] == "error"
    assert "RUNPOD_API_KEY" in events[-1]["message"]
    assert TEST_KEY not in events[-1]["message"]


def test_cloning_is_disabled_without_public_base_url(upstream, configure, client, tmp_path):
    configure(upstream)
    test_client = client()
    assert test_client.get("/health").json()["cloning_enabled"] is False
    clip = tmp_path / "clip.wav"
    from tests.conftest import make_wav

    clip.write_bytes(make_wav(1000, frames=FRAMERATE))
    response = test_client.post("/api/clone", files={"clip": ("clip.wav", clip.read_bytes(), "audio/wav")})
    assert response.status_code == 400
    assert "PUBLIC_BASE_URL" in response.json()["detail"]
    blocked = test_client.post("/api/speak", json={"text": "hello there", "clone_id": "0123456789ab"})
    assert blocked.status_code == 400
    assert "PUBLIC_BASE_URL" in blocked.json()["detail"]
    assert upstream.requests == []


def test_cloning_accepts_a_short_clip_and_rejects_a_long_one(upstream, configure, client, tmp_path, monkeypatch):
    configure(upstream)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://runpoddemo1.galaxygate.app")
    test_client = client()
    from tests.conftest import make_wav

    short = make_wav(900, frames=FRAMERATE * 5)
    response = test_client.post("/api/clone", files={"clip": ("me.wav", short, "audio/wav")})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["url"].startswith("https://runpoddemo1.galaxygate.app/clones/")
    assert body["seconds"] == pytest.approx(5.0, abs=0.05)
    long_clip = make_wav(900, frames=FRAMERATE * 31)
    rejected = test_client.post("/api/clone", files={"clip": ("long.wav", long_clip, "audio/wav")})
    assert rejected.status_code == 400
    assert "30 seconds" in rejected.json()["detail"]
    wrong_type = test_client.post("/api/clone", files={"clip": ("me.txt", b"hello", "text/plain")})
    assert wrong_type.status_code == 400
    assert ".txt is not accepted" in wrong_type.json()["detail"]


def test_a_clone_upload_is_sent_as_voice_url(upstream, configure, client, monkeypatch):
    configure(upstream)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://runpoddemo1.galaxygate.app")
    test_client = client()
    from tests.conftest import make_wav

    uploaded = test_client.post(
        "/api/clone", files={"clip": ("me.wav", make_wav(900, frames=FRAMERATE * 3), "audio/wav")}
    ).json()
    run_speak(test_client, "Read this in my voice please.", clone_id=uploaded["clone_id"])
    sent = json.loads(upstream.requests[0]["raw"])["input"]
    assert sent["voice_url"] == uploaded["url"]
    assert "voice" not in sent


def test_a_preview_is_generated_once_and_then_served_from_disk(upstream, configure, client):
    configure(upstream)
    test_client = client()
    first = test_client.get("/p/walter.wav")
    assert first.status_code == 200
    assert first.content[:4] == b"RIFF"
    second = test_client.get("/p/walter.wav")
    assert second.status_code == 200
    assert len(upstream.requests) == 1
    assert upstream.prompts() == [core.PREVIEW_SENTENCE]
    assert (core.data_dir() / "previews" / "walter.wav").is_file()


def test_an_unknown_voice_is_refused(upstream, configure, client):
    configure(upstream)
    test_client = client()
    assert test_client.get("/p/nobody.wav").status_code == 404
    response = test_client.post("/api/speak", json={"text": "hello there", "voice": "nobody"})
    assert response.status_code == 400
    assert upstream.requests == []


def test_empty_text_is_refused(upstream, configure, client):
    configure(upstream)
    response = client().post("/api/speak", json={"text": "   "})
    assert response.status_code == 400
    assert upstream.requests == []
