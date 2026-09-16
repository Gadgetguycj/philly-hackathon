import asyncio
import json
import logging
import os
import re
import secrets
import sqlite3
import string
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .core import MAX_NOTES_CHARS, downscale_jpeg, extract_html, jpeg_data_url, llm_model, stream_page

APP_DIR = Path(__file__).parent
STATIC_DIR = APP_DIR / "static"
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
SITES_DIR = DATA_DIR / "sites"
DB_PATH = DATA_DIR / "sketch.db"
SITE_ID_ALPHABET = string.ascii_letters + string.digits
SITE_ID_PATTERN = re.compile(r"^[A-Za-z0-9]{10}$")
PAGE_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; img-src data:",
    "X-Frame-Options": "SAMEORIGIN",
}
logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generation_limit() -> int:
    try:
        limit = int(os.getenv("MAX_GENERATIONS_PER_HOUR", "20"))
    except ValueError:
        return 20
    return limit if limit > 0 else 20


def data_dir_error() -> str:
    return (
        f"DATA_DIR {DATA_DIR} is not writable; create the host directory with "
        f"install -d -o 1000 -g 1000 {DATA_DIR}"
    )


def init_db() -> None:
    try:
        SITES_DIR.mkdir(parents=True, exist_ok=True)
        if not os.access(DATA_DIR, os.W_OK | os.X_OK):
            raise PermissionError(DATA_DIR)
        with sqlite3.connect(DB_PATH) as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS sites (
                id TEXT PRIMARY KEY, created_at TEXT NOT NULL, notes TEXT NOT NULL,
                model TEXT NOT NULL, tokens INTEGER)"""
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS generation_requests (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL)"
            )
    except OSError:
        logger.error("%s", data_dir_error())
        raise SystemExit(1) from None


def generation_usage(now: datetime | None = None) -> int:
    cutoff = ((now or utc_now()) - timedelta(hours=1)).isoformat()
    with sqlite3.connect(DB_PATH) as connection:
        return int(
            connection.execute(
                "SELECT COUNT(*) FROM generation_requests WHERE created_at > ?", (cutoff,)
            ).fetchone()[0]
        )


def reserve_generation() -> tuple[bool, datetime | None]:
    now = utc_now()
    cutoff = (now - timedelta(hours=1)).isoformat()
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("BEGIN IMMEDIATE")
        rows = connection.execute(
            "SELECT created_at FROM generation_requests WHERE created_at > ? ORDER BY created_at", (cutoff,)
        ).fetchall()
        if len(rows) >= generation_limit():
            return False, datetime.fromisoformat(rows[0][0]) + timedelta(hours=1)
        connection.execute("INSERT INTO generation_requests (created_at) VALUES (?)", (now.isoformat(),))
    return True, None


def new_site_id() -> str:
    return "".join(secrets.choice(SITE_ID_ALPHABET) for _ in range(10))


def save_site(html: str, photo: bytes, notes: str, tokens: int | None) -> str:
    site_id = new_site_id()
    directory = SITES_DIR / site_id
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "index.html").write_text(html, encoding="utf-8")
    (directory / "sketch.jpg").write_bytes(photo)
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            "INSERT INTO sites (id, created_at, notes, model, tokens) VALUES (?, ?, ?, ?, ?)",
            (site_id, utc_now().isoformat(), notes, llm_model(), tokens),
        )
    return site_id


def site_rows() -> list[dict]:
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT id, created_at, notes, model, tokens FROM sites ORDER BY created_at DESC, rowid DESC"
        ).fetchall()
    return [
        dict(row) | {"url": f"/s/{row['id']}/", "sketch_url": f"/s/{row['id']}/sketch.jpg"}
        for row in rows
    ]


def site_file(site_id: str, filename: str) -> Path:
    if not SITE_ID_PATTERN.match(site_id):
        raise HTTPException(404)
    path = SITES_DIR / site_id / filename
    if not path.is_file():
        raise HTTPException(404)
    return path


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Sketch to Site", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
async def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/sites", response_class=HTMLResponse)
async def sites_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "sites.html")


@app.get("/api/sites")
async def sites() -> list[dict]:
    return await asyncio.to_thread(site_rows)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "runpod_key_set": bool(os.getenv("RUNPOD_API_KEY", "").strip()),
        "model_configured": bool(os.getenv("LLM_BASE_URL", "").strip() or os.getenv("RUNPOD_ENDPOINT_ID", "").strip()),
    }


@app.get("/api/usage")
async def usage() -> dict:
    count = await asyncio.to_thread(generation_usage)
    limit = generation_limit()
    return {"count": count, "limit": limit, "remaining": max(limit - count, 0)}


@app.get("/s/{site_id}/sketch.jpg")
async def site_sketch(site_id: str) -> FileResponse:
    return FileResponse(site_file(site_id, "sketch.jpg"), media_type="image/jpeg")


@app.get("/s/{site_id}/", response_class=HTMLResponse)
async def site_page(site_id: str) -> FileResponse:
    return FileResponse(site_file(site_id, "index.html"), media_type="text/html", headers=PAGE_HEADERS)


@app.post("/api/sketch")
async def build_page(image: UploadFile = File(...), notes: str = Form("")):
    started = time.monotonic()
    notes = notes.strip()[:MAX_NOTES_CHARS]
    allowed, resets_at = await asyncio.to_thread(reserve_generation)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "detail": f"The hourly generation limit of {generation_limit()} was reached.",
                "resets_at": resets_at.isoformat() if resets_at else None,
            },
        )
    upload = await image.read()
    try:
        photo = await asyncio.to_thread(downscale_jpeg, upload)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    reported: dict = {}
    tokens = stream_page(jpeg_data_url(photo), notes, reported)
    try:
        first = await anext(tokens)
    except StopAsyncIteration:
        return JSONResponse(status_code=502, content={"detail": "The model returned an empty response."})
    except RuntimeError as exc:
        return JSONResponse(status_code=502, content={"detail": str(exc)})
    except httpx.HTTPError as exc:
        return JSONResponse(status_code=502, content={"detail": f"The model request failed: {exc}"})

    async def body():
        # The leading space tells the browser the model started writing. The body stays one JSON object.
        yield " "
        parts = [first]
        try:
            async for token in tokens:
                parts.append(token)
            html = extract_html("".join(parts))
            site_id = await asyncio.to_thread(save_site, html, photo, notes, reported.get("total_tokens"))
        except (RuntimeError, httpx.HTTPError, OSError) as exc:
            yield json.dumps({"detail": str(exc)})
            return
        yield json.dumps(
            {"id": site_id, "url": f"/s/{site_id}/", "elapsed_seconds": round(time.monotonic() - started, 1)}
        )

    return StreamingResponse(body(), media_type="application/json")
