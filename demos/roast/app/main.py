import asyncio
import json
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
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


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS roasts (id INTEGER PRIMARY KEY, repo TEXT NOT NULL, created_at TEXT NOT NULL, score INTEGER)"
        )


def save_roast(repo: str, score: int | None) -> None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            "INSERT INTO roasts (repo, created_at, score) VALUES (?, ?, ?)",
            (repo, datetime.now(timezone.utc).isoformat(), score),
        )


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
    return {"status": "ok"}


@app.post("/api/roast")
async def roast(request: RoastRequest) -> StreamingResponse:
    async def generate():
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
