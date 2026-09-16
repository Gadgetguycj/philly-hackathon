import asyncio
import sqlite3
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

from app import main


def test_init_db_migrates_existing_table_without_losing_rows(tmp_path, monkeypatch):
    database = tmp_path / "stickerwall.db"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """CREATE TABLE stickers (
            id INTEGER PRIMARY KEY, team TEXT NOT NULL, prompt TEXT NOT NULL,
            filename TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL)"""
        )
        connection.execute(
            "INSERT INTO stickers (team, prompt, filename, created_at) VALUES (?, ?, ?, ?)",
            ("team", "prompt", "existing.png", "2026-09-16T00:00:00+00:00"),
        )

    monkeypatch.setattr(main, "DB_PATH", database)
    monkeypatch.setattr(main, "STICKER_DIR", tmp_path / "stickers")
    main.init_db()
    main.init_db()

    with sqlite3.connect(database) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(stickers)")}
        row = connection.execute("SELECT filename, cost FROM stickers").fetchone()
    assert "cost" in columns
    assert row == ("existing.png", None)


def test_sticker_route_serves_jpeg_media_type(tmp_path, monkeypatch):
    sticker_dir = tmp_path / "stickers"
    sticker_dir.mkdir()
    (sticker_dir / "result.jpeg").write_bytes(b"\xff\xd8\xffjpeg bytes")
    monkeypatch.setattr(main, "STICKER_DIR", sticker_dir)
    response = asyncio.run(main.sticker_file("result.jpeg"))

    assert response.media_type == "image/jpeg"
    assert response.path == sticker_dir / "result.jpeg"


def configure_app_data(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "stickerwall.db")
    monkeypatch.setattr(main, "STICKER_DIR", tmp_path / "stickers")


def request_app(method, path, **kwargs):
    async def send():
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send())


def test_generation_limit_blocks_upstream_call_and_reports_usage(tmp_path, monkeypatch):
    configure_app_data(tmp_path, monkeypatch)
    monkeypatch.setenv("MAX_GENERATIONS_PER_HOUR", "1")
    calls = []

    async def fake_generate(prompt, output_dir):
        calls.append((prompt, output_dir))
        return SimpleNamespace(path=output_dir / "result.png", cost=None, response_shape="base64", bytes_written=10)

    monkeypatch.setattr(main, "generate_sticker", fake_generate)
    main.init_db()
    first = request_app("POST", "/api/stickers", json={"team": "Team", "prompt": "A robot"})
    blocked = request_app("POST", "/api/stickers", json={"team": "Team", "prompt": "A cat"})
    usage = request_app("GET", "/api/usage")

    assert first.status_code == 200
    assert blocked.status_code == 429
    assert blocked.json()["detail"]["message"] == "The hourly generation limit of 1 was reached."
    assert "resets_at" in blocked.json()["detail"]
    assert calls == [("A robot", tmp_path / "stickers")]
    assert usage.json() == {"count": 1, "limit": 1, "remaining": 0}


def test_generation_limit_resets_after_an_hour(tmp_path, monkeypatch):
    configure_app_data(tmp_path, monkeypatch)
    monkeypatch.setenv("MAX_GENERATIONS_PER_HOUR", "1")
    clock = datetime(2026, 9, 16, tzinfo=timezone.utc)
    monkeypatch.setattr(main, "now_utc", lambda: clock)
    calls = []

    async def fake_generate(prompt, output_dir):
        calls.append(prompt)
        return SimpleNamespace(path=output_dir / f"{prompt}.png", cost=None, response_shape="base64", bytes_written=10)

    monkeypatch.setattr(main, "generate_sticker", fake_generate)
    main.init_db()
    assert request_app("POST", "/api/stickers", json={"team": "Team", "prompt": "First"}).status_code == 200
    monkeypatch.setattr(main, "now_utc", lambda: clock + timedelta(hours=1))
    assert request_app("POST", "/api/stickers", json={"team": "Team", "prompt": "Second"}).status_code == 200

    assert calls == ["First", "Second"]


def test_usage_and_health_report_configuration_without_upstream_call(tmp_path, monkeypatch):
    configure_app_data(tmp_path, monkeypatch)
    monkeypatch.setenv("MAX_GENERATIONS_PER_HOUR", "3")
    monkeypatch.setenv("RUNPOD_API_KEY", "test-key")
    monkeypatch.setenv("FLUX_MODEL", "flux-test")
    main.init_db()
    health = request_app("GET", "/health")
    usage = request_app("GET", "/api/usage")

    assert health.json() == {"status": "ok", "runpod_key_set": True, "flux_model": "flux-test"}
    assert usage.json() == {"count": 0, "limit": 3, "remaining": 3}


def test_startup_exits_with_clear_data_directory_error(tmp_path, monkeypatch, caplog):
    missing_dir = tmp_path / "missing"
    monkeypatch.setattr(main, "DATA_DIR", missing_dir)

    with caplog.at_level("ERROR"), pytest.raises(SystemExit, match="1"):
        main.check_data_dir()

    assert str(missing_dir) in caplog.text
    assert f"install -d -o 1000 -g 1000 {missing_dir}" in caplog.text


@pytest.mark.parametrize("value", ["0", "-1", "not-a-number"])
def test_invalid_generation_limit_uses_default(value, monkeypatch):
    monkeypatch.setenv("MAX_GENERATIONS_PER_HOUR", value)

    assert main.generation_limit() == 30
