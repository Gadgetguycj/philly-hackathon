import asyncio
import re
import threading

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, StreamingResponse

from app import core

REAL_ASYNC_CLIENT = httpx.AsyncClient

DEFAULT_EVENTS = (
    '{"choices":[{"delta":{"content":"<!doctype html>"}}]}',
    '{"choices":[{"delta":{"content":"<html></html>"}}]}',
    "[DONE]",
)


def upstream_server(
    fail_status: int | None = None,
    fail_body: str = "worker cold start failed",
    events: tuple[str, ...] = DEFAULT_EVENTS,
    received: list | None = None,
    first_token_delay: float = 0.0,
) -> FastAPI:
    """A stand-in for the RunPod endpoint. Tests only; the app always calls the real upstream."""
    server = FastAPI()

    @server.post("/openai/v1/chat/completions")
    async def chat_completions(request: Request):
        assert request.headers["authorization"] == "Bearer test-key"
        payload = await request.json()
        assert payload["stream"] is True
        if received is not None:
            received.append(payload)
        if fail_status is not None:
            return PlainTextResponse(fail_body, status_code=fail_status)

        async def stream():
            if first_token_delay:
                await asyncio.sleep(first_token_delay)
            for item in events:
                yield f"data: {item}\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream")

    return server


@pytest.fixture
def streaming_upstream():
    """A real socket that writes the events one at a time, with a gap between them.

    The ASGI stand-in above cannot show a gap: httpx runs that app to completion and hands the
    whole reply over in one piece, so the app under test never waits between two tokens.
    """
    loops: list[asyncio.AbstractEventLoop] = []

    def configure(monkeypatch, events=DEFAULT_EVENTS, first_token_delay=0.0, token_gap=0.0) -> None:
        listening = threading.Event()
        address: dict = {}

        async def handle(reader, writer):
            head = await reader.readuntil(b"\r\n\r\n")
            await reader.readexactly(int(re.search(rb"content-length:\s*(\d+)", head, re.I).group(1)))
            writer.write(b"HTTP/1.1 200 OK\r\ncontent-type: text/event-stream\r\nconnection: close\r\n\r\n")
            await writer.drain()
            await asyncio.sleep(first_token_delay)
            for index, item in enumerate(events):
                if index:
                    await asyncio.sleep(token_gap)
                writer.write(f"data: {item}\n\n".encode())
                await writer.drain()
            writer.close()

        async def serve():
            server = await asyncio.start_server(handle, "127.0.0.1", 0)
            address["port"] = server.sockets[0].getsockname()[1]
            listening.set()
            async with server:
                await server.serve_forever()

        loop = asyncio.new_event_loop()
        loops.append(loop)

        def run() -> None:
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(serve())
            except RuntimeError:
                pass

        threading.Thread(target=run, daemon=True).start()
        assert listening.wait(5), "the streaming upstream never bound a port"
        monkeypatch.setenv("RUNPOD_API_KEY", "test-key")
        monkeypatch.setenv("LLM_BASE_URL", f"http://127.0.0.1:{address['port']}/openai/v1")

    yield configure
    for loop in loops:
        loop.call_soon_threadsafe(loop.stop)


@pytest.fixture
def fake_upstream():
    def configure(monkeypatch, **options) -> None:
        server = upstream_server(**options)

        def client(*args, **kwargs):
            kwargs["transport"] = httpx.ASGITransport(app=server)
            return REAL_ASYNC_CLIENT(*args, **kwargs)

        monkeypatch.setenv("RUNPOD_API_KEY", "test-key")
        monkeypatch.setenv("LLM_BASE_URL", "http://upstream/openai/v1")
        monkeypatch.setattr(core.httpx, "AsyncClient", client)

    return configure
