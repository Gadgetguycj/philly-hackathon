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
            for item in events:
                yield f"data: {item}\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream")

    return server


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
