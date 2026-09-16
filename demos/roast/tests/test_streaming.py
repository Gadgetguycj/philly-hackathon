import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, StreamingResponse

from app import core, main


def fake_openai_server(
    fail_status: int | None = None,
    fail_body: str = "worker cold start failed",
    stream_events: tuple[str, ...] | None = None,
) -> FastAPI:
    server = FastAPI()

    @server.post("/openai/v1/chat/completions")
    async def chat_completions(request: Request):
        assert request.headers["authorization"] == "Bearer test-key"
        assert (await request.json())["stream"] is True
        if fail_status is not None:
            return PlainTextResponse(fail_body, status_code=fail_status)

        async def events():
            if stream_events is not None:
                for stream_event in stream_events:
                    yield f"data: {stream_event}\n\n"
                return
            yield 'data: {"choices":[{"delta":{"content":"hello "}}]}\n\n'
            yield 'data: {"choices":[{"delta":{"content":"world"}}]}\n\n'
            yield "data: [DONE]\n\n"

        return StreamingResponse(events(), media_type="text/event-stream")

    return server


def configure_fake_openai(monkeypatch, **server_options) -> None:
    real_client = httpx.AsyncClient
    server = fake_openai_server(**server_options)

    def fake_client(*args, **kwargs):
        kwargs["transport"] = httpx.ASGITransport(app=server)
        return real_client(*args, **kwargs)

    monkeypatch.setenv("RUNPOD_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "http://test/openai/v1")
    monkeypatch.setattr(core.httpx, "AsyncClient", fake_client)


def configure_test_database(monkeypatch, tmp_path) -> None:
    async def run_in_place(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(main.asyncio, "to_thread", run_in_place)
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "roast.db")
    main.init_db()


async def fake_fetch_repository(_repo_url):
    return "owner/repo", [("main.py", "print('hello')")]


def test_stream_chat_reads_openai_compatible_sse(monkeypatch):
    configure_fake_openai(monkeypatch)

    async def collect():
        return [token async for token in core.stream_chat("test")]

    assert asyncio.run(collect()) == ["hello ", "world"]


def test_stream_chat_surfaces_upstream_error(monkeypatch):
    configure_fake_openai(monkeypatch, fail_status=503)

    async def collect():
        return [token async for token in core.stream_chat("test")]

    with pytest.raises(RuntimeError, match="worker cold start failed"):
        asyncio.run(collect())


def test_roast_http_402_emits_one_error_without_done_or_leaderboard(monkeypatch, tmp_path):
    error_body = '{"status":402,"title":"Insufficient Balance","detail":"insufficient balance"}'
    configure_fake_openai(monkeypatch, fail_status=402, fail_body=error_body)
    configure_test_database(monkeypatch, tmp_path)
    monkeypatch.setattr(main, "fetch_repository", fake_fetch_repository)

    async def request_roast():
        response = await main.roast(main.RoastRequest(repo_url="https://github.com/owner/repo"))
        body = "".join([chunk async for chunk in response.body_iterator])
        return body, await main.leaderboard()

    body, leaderboard = asyncio.run(request_roast())
    message = f"RunPod returned HTTP 402: {error_body}"

    assert body.count("event: error") == 1
    assert body.endswith(main.event("error", message))
    assert "event: done" not in body
    assert leaderboard == []


def test_roast_empty_stream_does_not_write_leaderboard_row(monkeypatch, tmp_path):
    configure_fake_openai(monkeypatch, stream_events=("[DONE]",))
    configure_test_database(monkeypatch, tmp_path)
    monkeypatch.setattr(main, "fetch_repository", fake_fetch_repository)

    async def request_roast():
        response = await main.roast(main.RoastRequest(repo_url="https://github.com/owner/repo"))
        body = "".join([chunk async for chunk in response.body_iterator])
        return body, await main.leaderboard()

    body, leaderboard = asyncio.run(request_roast())

    assert "event: done" in body
    assert leaderboard == []


def test_roast_accepts_final_usage_only_chunk(monkeypatch, tmp_path):
    real_client = httpx.AsyncClient
    configure_fake_openai(
        monkeypatch,
        stream_events=(
            '{"choices":[{"delta":{"content":"This repo "}}]}',
            '{"choices":[{"delta":{"content":"is crispy.\\n"}}]}',
            '{"choices":[{"delta":{"content":"SCORE: 7/10"}}]}',
            '{"id":"chatcmpl-...","object":"chat.completion.chunk","created":1789526179,"model":"Qwen/Qwen3-32B-AWQ","choices":[],"usage":{"prompt_tokens":4946,"total_tokens":6246,"completion_tokens":1300}}',
            "[DONE]",
        ),
    )
    configure_test_database(monkeypatch, tmp_path)
    monkeypatch.setattr(main, "fetch_repository", fake_fetch_repository)

    async def request_roast():
        transport = httpx.ASGITransport(app=main.app)
        async with real_client(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/roast", json={"repo_url": "https://github.com/owner/repo"})
        return response.text, await main.leaderboard()

    body, leaderboard = asyncio.run(request_roast())
    done_events = [
        json.loads(block.split("data: ", 1)[1])
        for block in body.strip().split("\n\n")
        if block.startswith("event: done\n")
    ]

    assert done_events == [{"repo": "owner/repo", "score": 7}]
    assert len(leaderboard) == 1


def test_fix_upstream_error_returns_json_502(monkeypatch, tmp_path):
    error_body = '{"status":402,"title":"Insufficient Balance","detail":"insufficient balance"}'
    configure_fake_openai(monkeypatch, fail_status=402, fail_body=error_body)
    configure_test_database(monkeypatch, tmp_path)
    monkeypatch.setattr(main, "fetch_repository", fake_fetch_repository)

    response = asyncio.run(main.fix(main.FixRequest(repo_url="https://github.com/owner/repo", roast="bad")))

    assert response.status_code == 502
    assert json.loads(response.body) == {"detail": f"RunPod returned HTTP 402: {error_body}"}


def test_generation_limit_emits_sse_error_without_upstream_call(monkeypatch, tmp_path):
    configure_test_database(monkeypatch, tmp_path)
    monkeypatch.setenv("MAX_GENERATIONS_PER_HOUR", "1")
    calls = 0

    async def upstream_would_be_called(_prompt):
        nonlocal calls
        calls += 1
        yield "unexpected"

    monkeypatch.setattr(main, "stream_chat", upstream_would_be_called)

    async def request_twice():
        await main.roast(main.RoastRequest(repo_url="https://github.com/owner/repo"))
        response = await main.roast(main.RoastRequest(repo_url="https://github.com/owner/repo"))
        return "".join([chunk async for chunk in response.body_iterator])

    body = asyncio.run(request_twice())

    assert body.count("event: error") == 1
    assert "hourly generation limit of 1 was reached" in body
    assert calls == 0


def test_fix_generation_limit_emits_sse_error_without_upstream_call(monkeypatch, tmp_path):
    configure_test_database(monkeypatch, tmp_path)
    monkeypatch.setenv("MAX_GENERATIONS_PER_HOUR", "1")
    main.reserve_generation()
    calls = 0

    async def upstream_would_be_called(_prompt):
        nonlocal calls
        calls += 1
        yield "unexpected"

    monkeypatch.setattr(main, "stream_chat", upstream_would_be_called)

    async def request_fix():
        response = await main.fix(main.FixRequest(repo_url="https://github.com/owner/repo", roast="bad"))
        return "".join([chunk async for chunk in response.body_iterator])

    body = asyncio.run(request_fix())

    assert body.count("event: error") == 1
    assert "hourly generation limit of 1 was reached" in body
    assert calls == 0


def test_generation_limit_resets_after_one_hour(monkeypatch, tmp_path):
    configure_test_database(monkeypatch, tmp_path)
    monkeypatch.setenv("MAX_GENERATIONS_PER_HOUR", "1")
    current = datetime(2026, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(main, "utc_now", lambda: current)

    allowed, _ = main.reserve_generation()
    assert allowed is True
    current += timedelta(minutes=59)
    allowed, reset_at = main.reserve_generation()
    assert allowed is False
    assert reset_at == datetime(2026, 1, 1, 1, tzinfo=timezone.utc)
    current += timedelta(minutes=1)
    allowed, _ = main.reserve_generation()
    assert allowed is True


def test_usage_reports_current_count_and_limit(monkeypatch, tmp_path):
    configure_test_database(monkeypatch, tmp_path)
    monkeypatch.setenv("MAX_GENERATIONS_PER_HOUR", "3")
    main.reserve_generation()
    main.reserve_generation()

    assert asyncio.run(main.usage()) == {"count": 2, "limit": 3}


def test_health_reports_configuration_without_calling_runpod(monkeypatch):
    monkeypatch.setenv("RUNPOD_API_KEY", "test-key")
    monkeypatch.setenv("RUNPOD_ENDPOINT_ID", "endpoint")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)

    assert asyncio.run(main.health()) == {
        "status": "ok",
        "runpod_key_set": True,
        "model_configured": True,
    }


def test_startup_exits_with_clear_data_directory_error(monkeypatch, tmp_path, caplog):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main.os, "access", lambda *_: False)

    with caplog.at_level("ERROR"), pytest.raises(SystemExit, match="1"):
        main.init_db()

    assert str(data_dir) in caplog.text
    assert f"install -d -o 1000 -g 1000 {data_dir}" in caplog.text
