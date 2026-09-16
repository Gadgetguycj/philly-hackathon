import asyncio
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException

from app import main
from tests.conftest import REAL_ASYNC_CLIENT

SAMPLE = Path(__file__).resolve().parent.parent / "samples" / "sketch.jpg"

# One second of a scenario runs as SCALE real seconds, so a 25 second cold start takes a quarter of a second.
SCALE = 0.01

HTML_EVENTS = (
    '{"choices":[{"delta":{"content":"```html\\n<!doctype html>\\n<html><head><style>'
    'body{font-family:sans-serif}</style></head><body>"}}]}',
    '{"choices":[{"delta":{"content":"<h1>HEADER</h1><p>CARD 1</p></body></html>\\n```"},'
    '"finish_reason":"stop"}]}',
    '{"choices":[],"usage":{"prompt_tokens":1200,"completion_tokens":420,"total_tokens":1620}}',
    "[DONE]",
)


def configure_app(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    monkeypatch.setattr(main, "SITES_DIR", tmp_path / "sites")
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "sketch.db")
    main.init_db()


def request_app(method, path, **kwargs):
    async def send():
        transport = main.httpx.ASGITransport(app=main.app)
        async with REAL_ASYNC_CLIENT(transport=transport, base_url="http://test", timeout=30) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send())


def post_sketch(image: bytes = None, notes: str = ""):
    return request_app(
        "POST",
        "/api/sketch",
        files={"image": ("sketch.jpg", image if image is not None else SAMPLE.read_bytes(), "image/jpeg")},
        data={"notes": notes},
    )


def sketch_chunks(notes: str = "") -> tuple[dict, list[bytes]]:
    """Posts a sketch straight to the ASGI app, so every flushed chunk stays a message of its own."""
    request = main.httpx.Request(
        "POST",
        "http://test/api/sketch",
        files={"image": ("sketch.jpg", SAMPLE.read_bytes(), "image/jpeg")},
        data={"notes": notes},
    )
    payload = request.read()
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/sketch",
        "raw_path": b"/api/sketch",
        "query_string": b"",
        "headers": [(key.lower(), value) for key, value in request.headers.raw],
        "client": ("127.0.0.1", 123),
        "server": ("test", 80),
        "root_path": "",
    }
    messages: list[dict] = []

    async def run():
        async def receive():
            return {"type": "http.request", "body": payload, "more_body": False}

        async def send(message):
            messages.append(message)

        await main.app(scope, receive, send)

    asyncio.run(run())
    start = next(message for message in messages if message["type"] == "http.response.start")
    chunks = [m["body"] for m in messages if m["type"] == "http.response.body" and m.get("body")]
    return start, chunks


def test_end_to_end_request_builds_hosts_and_lists_the_page(monkeypatch, tmp_path, fake_upstream):
    received: list = []
    fake_upstream(monkeypatch, events=HTML_EVENTS, received=received)
    configure_app(monkeypatch, tmp_path)
    monkeypatch.setenv("LLM_MODEL", "Qwen/Qwen2.5-VL-7B-Instruct")

    response = post_sketch(notes="Ada's Garage")
    body = response.json()

    assert response.status_code == 200
    assert body["url"] == f"/s/{body['id']}/"
    assert len(body["id"]) == 10
    assert isinstance(body["elapsed_seconds"], float)
    # The server flushes one whitespace byte when the model starts writing, so the phone can show progress.
    assert response.text.startswith(" ")

    sent = received[0]["messages"][1]["content"]
    assert sent[0] == {"type": "text", "text": "Ada's Garage"}
    assert sent[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")

    page = request_app("GET", body["url"])
    assert page.status_code == 200
    assert page.text.startswith("<!doctype html>")
    assert page.text.endswith("</html>")
    assert "```" not in page.text

    sketch = request_app("GET", f"{body['url']}sketch.jpg")
    assert sketch.status_code == 200
    assert sketch.headers["content-type"] == "image/jpeg"
    assert sketch.content.startswith(b"\xff\xd8\xff")

    listed = request_app("GET", "/api/sites").json()
    assert [row["id"] for row in listed] == [body["id"]]
    assert listed[0]["notes"] == "Ada's Garage"
    assert listed[0]["model"] == "Qwen/Qwen2.5-VL-7B-Instruct"
    assert listed[0]["tokens"] == 1620
    assert listed[0]["sketch_url"] == f"/s/{body['id']}/sketch.jpg"


def test_keep_alive_bytes_are_flushed_while_the_model_is_still_thinking(monkeypatch, tmp_path, fake_upstream):
    fake_upstream(monkeypatch, events=HTML_EVENTS, first_token_delay=25 * SCALE)
    configure_app(monkeypatch, tmp_path)
    monkeypatch.setenv("KEEPALIVE_INTERVAL_SECONDS", str(10 * SCALE))

    start, chunks = sketch_chunks()
    first_content = next(index for index, chunk in enumerate(chunks) if chunk.strip())
    waiting = chunks[:first_content]
    body = json.loads(b"".join(chunks))

    assert start["status"] == 200
    # Two keep-alive newlines land during a 25 second wait at a 10 second interval, well inside
    # the 100 seconds of silence that makes Cloudflare give up on the connection.
    assert waiting.count(b"\n") >= 2
    assert waiting[-1] == b" "
    assert body["url"] == f"/s/{body['id']}/"
    assert request_app("GET", body["url"]).status_code == 200


def test_generated_page_carries_the_content_security_policy(monkeypatch, tmp_path, fake_upstream):
    fake_upstream(monkeypatch, events=HTML_EVENTS)
    configure_app(monkeypatch, tmp_path)

    url = post_sketch().json()["url"]
    page = request_app("GET", url)

    assert page.headers["content-security-policy"] == "default-src 'none'; style-src 'unsafe-inline'; img-src data:"
    assert page.headers["x-frame-options"] == "SAMEORIGIN"
    assert page.headers["content-type"].startswith("text/html")


def test_site_ids_are_validated_before_the_filesystem_is_touched(monkeypatch, tmp_path):
    configure_app(monkeypatch, tmp_path)
    outside = tmp_path / "escaped"
    outside.mkdir()
    (outside / "index.html").write_text("<html>not a generated page</html>")

    assert request_app("GET", "/s/AbCdEfGhIj/").status_code == 404
    with pytest.raises(HTTPException) as refused:
        main.site_file("../escaped", "index.html")
    assert refused.value.status_code == 404


def test_hourly_cap_blocks_the_second_request_without_calling_the_model(monkeypatch, tmp_path, fake_upstream):
    received: list = []
    fake_upstream(monkeypatch, events=HTML_EVENTS, received=received)
    configure_app(monkeypatch, tmp_path)
    monkeypatch.setenv("MAX_GENERATIONS_PER_HOUR", "1")

    first = post_sketch()
    blocked = post_sketch()
    usage = request_app("GET", "/api/usage").json()

    assert first.status_code == 200
    assert blocked.status_code == 429
    assert blocked.json()["detail"] == "The hourly generation limit of 1 was reached."
    assert blocked.json()["resets_at"]
    assert len(received) == 1
    assert usage == {"count": 1, "limit": 1, "remaining": 0}


def test_a_failed_generation_gives_its_slot_back_and_a_built_page_keeps_it(monkeypatch, tmp_path, fake_upstream):
    configure_app(monkeypatch, tmp_path)
    monkeypatch.setenv("MAX_GENERATIONS_PER_HOUR", "2")
    monkeypatch.setenv("RUNPOD_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:1/openai/v1")

    unreachable = post_sketch()
    fake_upstream(monkeypatch, fail_status=402, fail_body="worker cold start failed")
    refused = post_sketch()
    fake_upstream(monkeypatch, events=("[DONE]",))
    empty = post_sketch()

    assert [unreachable.status_code, refused.status_code, empty.status_code] == [502, 502, 502]
    assert empty.json() == {"detail": "The model returned an empty response."}
    assert request_app("GET", "/api/usage").json() == {"count": 0, "limit": 2, "remaining": 2}

    fake_upstream(monkeypatch, events=HTML_EVENTS)
    built = post_sketch()

    assert built.json()["url"]
    assert request_app("GET", "/api/usage").json() == {"count": 1, "limit": 2, "remaining": 1}


def test_hourly_cap_resets_after_an_hour(monkeypatch, tmp_path):
    configure_app(monkeypatch, tmp_path)
    monkeypatch.setenv("MAX_GENERATIONS_PER_HOUR", "2")
    clock = datetime(2026, 9, 16, 10, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(main, "utc_now", lambda: clock)

    assert main.reserve_generation()[0] is not None
    assert main.reserve_generation()[0] is not None
    request_id, resets_at = main.reserve_generation()
    assert request_id is None
    assert resets_at == clock + timedelta(hours=1)

    clock += timedelta(hours=1, seconds=1)
    assert main.reserve_generation()[0] is not None


@pytest.mark.parametrize("value", ["0", "-4", "not-a-number"])
def test_invalid_generation_limit_uses_the_default(value, monkeypatch):
    monkeypatch.setenv("MAX_GENERATIONS_PER_HOUR", value)

    assert main.generation_limit() == 20


def test_upstream_error_body_is_returned_verbatim_as_502(monkeypatch, tmp_path, fake_upstream):
    failure = '{"status":402,"title":"Insufficient Balance","detail":"insufficient balance"}'
    fake_upstream(monkeypatch, fail_status=402, fail_body=failure)
    configure_app(monkeypatch, tmp_path)

    response = post_sketch()

    assert response.status_code == 502
    assert response.json() == {"detail": f"RunPod returned HTTP 402: {failure}"}
    assert request_app("GET", "/api/sites").json() == []


def test_reply_without_a_document_is_reported_and_stores_nothing(monkeypatch, tmp_path, fake_upstream):
    fake_upstream(
        monkeypatch,
        events=('{"choices":[{"delta":{"content":"I cannot read the photograph."}}]}', "[DONE]"),
    )
    configure_app(monkeypatch, tmp_path)

    body = post_sketch().json()

    assert body["detail"] == "The model did not return a complete HTML document."
    assert "url" not in body
    assert request_app("GET", "/api/sites").json() == []
    assert not list((tmp_path / "sites").iterdir())
    assert request_app("GET", "/api/usage").json()["count"] == 0


def test_upload_that_is_not_an_image_returns_400(monkeypatch, tmp_path, fake_upstream):
    fake_upstream(monkeypatch, events=HTML_EVENTS)
    configure_app(monkeypatch, tmp_path)

    response = post_sketch(image=b"not an image at all")

    assert response.status_code == 400
    assert response.json() == {"detail": "The upload was not a readable image."}


def test_saved_photo_is_downscaled_and_recorded(monkeypatch, tmp_path, fake_upstream):
    fake_upstream(monkeypatch, events=HTML_EVENTS)
    configure_app(monkeypatch, tmp_path)

    site_id = post_sketch().json()["id"]
    saved = (tmp_path / "sites" / site_id / "sketch.jpg").read_bytes()

    with sqlite3.connect(tmp_path / "sketch.db") as connection:
        rows = connection.execute("SELECT id, tokens FROM sites").fetchall()
    assert rows == [(site_id, 1620)]
    assert len(saved) < SAMPLE.stat().st_size
    assert json.loads(request_app("GET", "/api/usage").text)["count"] == 1


def test_health_reports_configuration_without_calling_the_model(monkeypatch):
    monkeypatch.setenv("RUNPOD_API_KEY", "test-key")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.setenv("RUNPOD_ENDPOINT_ID", "endpoint")

    assert asyncio.run(main.health()) == {"status": "ok", "runpod_key_set": True, "model_configured": True}

    monkeypatch.delenv("RUNPOD_ENDPOINT_ID")
    monkeypatch.delenv("RUNPOD_API_KEY")
    assert asyncio.run(main.health()) == {"status": "ok", "runpod_key_set": False, "model_configured": False}


def test_startup_exits_with_a_clear_data_directory_error(monkeypatch, tmp_path, caplog):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "SITES_DIR", data_dir / "sites")
    monkeypatch.setattr(main.os, "access", lambda *_: False)

    with caplog.at_level("ERROR"), pytest.raises(SystemExit, match="1"):
        main.init_db()

    assert f"install -d -o 1000 -g 1000 {data_dir}" in caplog.text
