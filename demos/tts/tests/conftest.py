"""Test doubles and fixtures.

The stand-in upstream here answers on a real socket with the documented
Chatterbox Turbo response shape and a real wav, so the app's own HTTP client,
JSON parsing and wav handling all run for real during the tests.
"""

from __future__ import annotations

import io
import json
import threading
import time
import wave
import zlib
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient

FRAMERATE = 24000
CHANNELS = 1
SAMPLE_WIDTH = 2
CHUNK_FRAMES = 1200


def marker_for(prompt: str) -> int:
    """A per prompt amplitude, so an assembled file proves which chunk went where."""
    return 1000 + zlib.crc32(prompt.encode("utf-8")) % 20000


def make_wav(amplitude: int, frames: int = CHUNK_FRAMES) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(CHANNELS)
        handle.setsampwidth(SAMPLE_WIDTH)
        handle.setframerate(FRAMERATE)
        handle.writeframes(amplitude.to_bytes(2, "little", signed=True) * frames)
    return buffer.getvalue()


class FakeUpstream:
    """A throwaway Chatterbox Turbo stand-in on localhost."""

    def __init__(self) -> None:
        self.status = 200
        self.body: str | None = None
        self.delay = 0.0
        self.requests: list[dict] = []
        self.lock = threading.Lock()
        self.audio: dict[str, bytes] = {}
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/v2/chatterbox-turbo"

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def prompts(self) -> list[str]:
        with self.lock:
            return [item["prompt"] for item in self.requests if "prompt" in item]

    def _handler(self):
        upstream = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args) -> None:
                return

            def _send(self, code: int, payload: bytes, content_type: str) -> None:
                self.send_response(code)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self) -> None:
                key = self.path.rsplit("/", 1)[-1]
                with upstream.lock:
                    audio = upstream.audio.get(key)
                if audio is None:
                    self._send(404, b"no audio", "text/plain")
                    return
                self._send(200, audio, "audio/wav")

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length)
                try:
                    prompt = json.loads(raw)["input"]["prompt"]
                except (ValueError, KeyError, TypeError):
                    prompt = ""
                with upstream.lock:
                    upstream.requests.append(
                        {
                            "at": time.monotonic(),
                            "prompt": prompt,
                            "authorization": self.headers.get("Authorization", ""),
                            "raw": raw.decode("utf-8", "replace"),
                        }
                    )
                    status = upstream.status
                    body = upstream.body
                    delay = upstream.delay
                if delay:
                    time.sleep(delay)
                if status != 200:
                    text = body if body is not None else (
                        "upstream refused, token was "
                        f"{self.headers.get('Authorization', '')}"
                    )
                    self._send(status, text.encode(), "text/plain")
                    return
                name = f"{len(upstream.requests):04d}.wav"
                with upstream.lock:
                    upstream.audio[name] = make_wav(marker_for(prompt))
                payload = {
                    "id": f"sync-{name}",
                    "status": "COMPLETED",
                    "delayTime": 10,
                    "executionTime": 1856,
                    "output": {"audio_url": f"http://127.0.0.1:{upstream.port}/audio/{name}"},
                }
                self._send(200, json.dumps(payload).encode(), "application/json")

        return Handler


TEST_KEY = "rpa_TESTKEY_do_not_leak_0123456789abcdef"


@pytest.fixture
def upstream():
    fake = FakeUpstream()
    try:
        yield fake
    finally:
        fake.close()


@pytest.fixture
def configure(monkeypatch, tmp_path):
    def apply(upstream: FakeUpstream | None = None, **overrides) -> None:
        monkeypatch.setenv("RUNPOD_API_KEY", overrides.pop("key", TEST_KEY))
        monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
        monkeypatch.setenv("MAX_WORDS", str(overrides.pop("max_words", 2000)))
        monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
        if upstream is not None:
            monkeypatch.setenv("TTS_ENDPOINT", upstream.base_url)
        for name, value in overrides.items():
            monkeypatch.setenv(name.upper(), str(value))

    return apply


@pytest.fixture
def live_server():
    """A real uvicorn on a real socket, for the tests that watch the stream arrive."""
    import uvicorn

    from app.main import app

    running: list[tuple] = []

    def make() -> str:
        config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning")
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.02)
        if not server.started:
            raise RuntimeError("the test server did not start")
        port = server.servers[0].sockets[0].getsockname()[1]
        running.append((server, thread))
        return f"http://127.0.0.1:{port}"

    try:
        yield make
    finally:
        for server, thread in running:
            server.should_exit = True
            thread.join(timeout=10)


@pytest.fixture
def client():
    """A factory, so a test can set the environment before the app starts."""
    from app.main import app

    stack = ExitStack()

    def make() -> TestClient:
        return stack.enter_context(TestClient(app))

    try:
        yield make
    finally:
        stack.close()


def read_events(response) -> list[dict]:
    events = []
    for line in response.iter_lines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events
