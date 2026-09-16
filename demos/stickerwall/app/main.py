import asyncio
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .core import generate_sticker

APP_DIR = Path(__file__).parent
STATIC_DIR = APP_DIR / "static"
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
STICKER_DIR = DATA_DIR / "stickers"
DB_PATH = DATA_DIR / "stickerwall.db"


def init_db() -> None:
    STICKER_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS stickers (
            id INTEGER PRIMARY KEY, team TEXT NOT NULL, prompt TEXT NOT NULL,
            filename TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL, cost REAL)"""
        )
        columns = {row[1] for row in connection.execute("PRAGMA table_info(stickers)")}
        if "cost" not in columns:
            connection.execute("ALTER TABLE stickers ADD COLUMN cost REAL")


def save_row(team: str, prompt: str, filename: str, cost: float | None = None) -> dict:
    created_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            "INSERT INTO stickers (team, prompt, filename, created_at, cost) VALUES (?, ?, ?, ?, ?)",
            (team, prompt, filename, created_at, cost),
        )
        sticker_id = cursor.lastrowid
    return {
        "id": sticker_id,
        "team": team,
        "prompt": prompt,
        "filename": filename,
        "created_at": created_at,
        "cost": cost,
    }


def list_rows() -> list[dict]:
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT id, team, prompt, filename, created_at, cost FROM stickers ORDER BY created_at DESC, id DESC"
        ).fetchall()
    return [dict(row) | {"image_url": f"/stickers/{row['filename']}"} for row in rows]


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="The Sticker Wall", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class StickerRequest(BaseModel):
    team: str = Field(min_length=1, max_length=80)
    prompt: str = Field(min_length=1, max_length=1_000)


@app.get("/", response_class=HTMLResponse)
async def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/wall", response_class=HTMLResponse)
async def wall() -> FileResponse:
    return FileResponse(STATIC_DIR / "wall.html")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/stickers")
async def stickers() -> list[dict]:
    return await asyncio.to_thread(list_rows)


@app.get("/stickers/{filename}")
async def sticker_file(filename: str) -> FileResponse:
    if Path(filename).name != filename:
        raise HTTPException(404)
    path = STICKER_DIR / filename
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path)


@app.post("/api/stickers")
async def create_sticker(request: StickerRequest) -> dict:
    try:
        result = await generate_sticker(request.prompt, STICKER_DIR)
    except RuntimeError as exc:
        raise HTTPException(502, detail=str(exc)) from exc
    row = await asyncio.to_thread(
        save_row, request.team.strip(), request.prompt.strip(), result.path.name, result.cost
    )
    return row | {
        "image_url": f"/stickers/{result.path.name}",
        "response_shape": result.response_shape,
        "bytes_written": result.bytes_written,
    }
