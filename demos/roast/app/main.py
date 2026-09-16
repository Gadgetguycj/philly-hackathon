import asyncio
import json
import logging
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .core import build_fix_prompt, build_roast_prompt, fetch_repository, parse_score, stream_chat

APP_DIR = Path(__file__).parent
STATIC_DIR = APP_DIR / "static"
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
DB_PATH = DATA_DIR / "roast.db"
logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generation_limit() -> int:
    try:
        limit = int(os.getenv("MAX_GENERATIONS_PER_HOUR", "30"))
    except ValueError:
        return 30
    return limit if limit > 0 else 30


def data_dir_error() -> str:
    return (
        f"DATA_DIR {DATA_DIR} is not writable; create the host directory with "
        f"install -d -o 1000 -g 1000 {DATA_DIR}"
    )


def init_db() -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not os.access(DATA_DIR, os.W_OK | os.X_OK):
            raise PermissionError(DATA_DIR)
        with sqlite3.connect(DB_PATH) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS roasts (id INTEGER PRIMARY KEY, repo TEXT NOT NULL, created_at TEXT NOT NULL, score INTEGER)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS generation_requests (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL)"
            )
    except OSError:
        logger.error("%s", data_dir_error())
        raise SystemExit(1) from None


def save_roast(repo: str, score: int | None) -> None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            "INSERT INTO roasts (repo, created_at, score) VALUES (?, ?, ?)",
            (repo, utc_now().isoformat(), score),
        )


def generation_usage(now: datetime | None = None) -> int:
    now = now or utc_now()
    cutoff = (now - timedelta(hours=1)).isoformat()
    with sqlite3.connect(DB_PATH) as connection:
        return int(connection.execute(
            "SELECT COUNT(*) FROM generation_requests WHERE created_at > ?", (cutoff,)
        ).fetchone()[0])


def reserve_generation() -> tuple[bool, datetime | None]:
    now = utc_now()
    cutoff = (now - timedelta(hours=1)).isoformat()
    limit = generation_limit()
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("BEGIN IMMEDIATE")
        rows = connection.execute(
            "SELECT created_at FROM generation_requests WHERE created_at > ? ORDER BY created_at", (cutoff,)
        ).fetchall()
        if len(rows) >= limit:
            return False, datetime.fromisoformat(rows[0][0]) + timedelta(hours=1)
        connection.execute("INSERT INTO generation_requests (created_at) VALUES (?)", (now.isoformat(),))
    return True, None


def leaderboard_rows() -> list[dict]:
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """SELECT repo, COUNT(*) AS roast_count, ROUND(AVG(score), 1) AS average_score,
            MAX(created_at) AS last_roasted FROM roasts GROUP BY repo
            ORDER BY roast_count DESC, last_roasted DESC"""
        ).fetchall()
    return [dict(row) for row in rows]


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Roast My Repo", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class RoastRequest(BaseModel):
    repo_url: str


class FixRequest(BaseModel):
    repo_url: str
    roast: str


def event(kind: str, value: object) -> str:
    return f"event: {kind}\ndata: {json.dumps(value)}\n\n"


@app.get("/", response_class=HTMLResponse)
async def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "leaderboard.html")


@app.get("/api/leaderboard")
async def leaderboard() -> list[dict]:
    return await asyncio.to_thread(leaderboard_rows)


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
    return {"count": count, "limit": generation_limit()}


def limit_error(resets_at: datetime) -> str:
    return f"The hourly generation limit of {generation_limit()} was reached. It resets at {resets_at.isoformat()}."


@app.post("/api/roast")
async def roast(request: RoastRequest) -> StreamingResponse:
    allowed, resets_at = await asyncio.to_thread(reserve_generation)

    async def generate():
        if not allowed:
            yield event("error", limit_error(resets_at))
            return
        try:
            yield event("status", "Reading the repository")
            repo, files = await fetch_repository(request.repo_url)
            yield event("status", "GPU is waking up")
            answer: list[str] = []
            first = True
            async for token in stream_chat(build_roast_prompt(repo, files)):
                if first:
                    yield event("status", "Writing the roast")
                    first = False
                answer.append(token)
                yield event("token", token)
            text = "".join(answer)
            score = parse_score(text)
            if answer:
                await asyncio.to_thread(save_roast, repo, score)
            yield event("done", {"repo": repo, "score": score})
        except Exception as exc:
            yield event("error", str(exc))
    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.post("/api/fix")
async def fix(request: FixRequest):
    allowed, resets_at = await asyncio.to_thread(reserve_generation)
    if not allowed:
        async def limit_reached():
            yield event("error", limit_error(resets_at))
        return StreamingResponse(limit_reached(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
    try:
        repo, files = await fetch_repository(request.repo_url)
        tokens = [token async for token in stream_chat(build_fix_prompt(repo, request.roast, files))]
    except Exception as exc:
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    async def generate():
        yield event("status", "Reading the repository")
        yield event("status", "GPU is waking up")
        if tokens:
            yield event("status", "Writing the patch")
        for token in tokens:
            yield event("token", token)
        yield event("done", {"repo": repo})

    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
