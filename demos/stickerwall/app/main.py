import logging
import os
import sqlite3
from contextlib import asynccontextmanager, closing
from datetime import datetime, timedelta, timezone
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
logger = logging.getLogger(__name__)


def now_utc() -> datetime:
    """Return the current time so tests can control the rate-limit window."""
    return datetime.now(timezone.utc)


def generation_limit() -> int:
    try:
        limit = int(os.getenv("MAX_GENERATIONS_PER_HOUR", "30"))
    except ValueError:
        return 30
    return limit if limit > 0 else 30


def check_data_dir() -> None:
    if DATA_DIR.is_dir() and os.access(DATA_DIR, os.W_OK | os.X_OK):
        return
    logger.error(
        "DATA_DIR %s is not writable. Create the host directory with: install -d -o 1000 -g 1000 %s",
        DATA_DIR,
        DATA_DIR,
    )
    raise SystemExit(1)


def init_db() -> None:
    STICKER_DIR.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS stickers (
            id INTEGER PRIMARY KEY, team TEXT NOT NULL, prompt TEXT NOT NULL,
            filename TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL, cost REAL)"""
        )
        columns = {row[1] for row in connection.execute("PRAGMA table_info(stickers)")}
        if "cost" not in columns:
            connection.execute("ALTER TABLE stickers ADD COLUMN cost REAL")
        connection.execute(
            """CREATE TABLE IF NOT EXISTS generation_requests (
            id INTEGER PRIMARY KEY, created_at TEXT NOT NULL)"""
        )


def current_generation_count(at: datetime | None = None) -> int:
    cutoff = (at or now_utc()) - timedelta(hours=1)
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        return connection.execute(
            "SELECT COUNT(*) FROM generation_requests WHERE created_at > ?", (cutoff.isoformat(),)
        ).fetchone()[0]


def reserve_generation() -> tuple[bool, datetime | None]:
    current_time = now_utc()
    cutoff = current_time - timedelta(hours=1)
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        count = connection.execute(
            "SELECT COUNT(*) FROM generation_requests WHERE created_at > ?", (cutoff.isoformat(),)
        ).fetchone()[0]
        if count >= generation_limit():
            oldest = connection.execute(
                "SELECT MIN(created_at) FROM generation_requests WHERE created_at > ?", (cutoff.isoformat(),)
            ).fetchone()[0]
            return False, datetime.fromisoformat(oldest) + timedelta(hours=1)
        connection.execute("INSERT INTO generation_requests (created_at) VALUES (?)", (current_time.isoformat(),))
    return True, None


def save_row(team: str, prompt: str, filename: str, cost: float | None = None) -> dict:
    created_at = datetime.now(timezone.utc).isoformat()
    with closing(sqlite3.connect(DB_PATH)) as connection, connection:
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
    with closing(sqlite3.connect(DB_PATH)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT id, team, prompt, filename, created_at, cost FROM stickers ORDER BY created_at DESC, id DESC"
        ).fetchall()
    return [dict(row) | {"image_url": f"/stickers/{row['filename']}"} for row in rows]


@asynccontextmanager
async def lifespan(_: FastAPI):
    check_data_dir()
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
    return {
        "status": "ok",
        "runpod_key_set": bool(os.getenv("RUNPOD_API_KEY")),
        "flux_model": os.getenv("FLUX_MODEL", "black-forest-labs-flux-1-schnell"),
    }


@app.get("/api/usage")
async def usage() -> dict:
    count = current_generation_count()
    limit = generation_limit()
    return {"count": count, "limit": limit, "remaining": max(limit - count, 0)}


@app.get("/api/stickers")
async def stickers() -> list[dict]:
    return list_rows()


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
    allowed, resets_at = reserve_generation()
    if not allowed:
        raise HTTPException(
            429,
            detail={
                "message": f"The hourly generation limit of {generation_limit()} was reached.",
                "resets_at": resets_at.isoformat() if resets_at else None,
            },
        )
    try:
        result = await generate_sticker(request.prompt, STICKER_DIR)
    except RuntimeError as exc:
        raise HTTPException(502, detail=str(exc)) from exc
    row = save_row(request.team.strip(), request.prompt.strip(), result.path.name, result.cost)
    return row | {
        "image_url": f"/stickers/{result.path.name}",
        "response_shape": result.response_shape,
        "bytes_written": result.bytes_written,
    }
