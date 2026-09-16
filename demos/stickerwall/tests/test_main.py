import asyncio
import sqlite3

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
