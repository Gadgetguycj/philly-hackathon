"""Bookbuilder. A book idea in, a hundred pages out, streamed page by page."""

import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import config, render, runs, store

APP_DIR = Path(__file__).parent
STATIC_DIR = APP_DIR / "static"
# A quiet event stream gets cut by a proxy, so nothing on the wire stays silent this long.
HEARTBEAT_SECONDS = 10.0
MAX_IDEA_CHARS = 2000
MAX_TITLE_CHARS = 200
SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("bookbuilder")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        store.prepare()
    except (OSError, PermissionError) as error:
        logger.error("%s", error if str(error) else store.data_dir_error())
        raise SystemExit(1) from None
    logger.info(
        "bookbuilder ready model=%s base_url=%s key_set=%s pages=%s data_dir=%s",
        config.model(),
        config.base_url(),
        bool(config.api_key()),
        config.default_pages(),
        config.data_dir(),
    )
    yield


app = FastAPI(title="Bookbuilder", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=FileResponse)
async def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html")


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "runpod_key_set": bool(config.api_key()),
            "model": config.model(),
            "base_url_set": bool(config.base_url()),
        }
    )


@app.get("/api/config")
async def api_config() -> JSONResponse:
    return JSONResponse(
        {
            "model": config.model(),
            "default_pages": config.default_pages(),
            "page_choices": config.page_choices(),
            "runpod_key_set": bool(config.api_key()),
        }
    )


@app.post("/api/runs")
async def create_run(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="The request body was not JSON.") from None
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="The request body was not a JSON object.")
    idea = str(body.get("idea") or "").strip()[:MAX_IDEA_CHARS]
    title = " ".join(str(body.get("title") or "").split())[:MAX_TITLE_CHARS]
    if not idea:
        raise HTTPException(status_code=400, detail="Type an idea for the book first.")
    pages = body.get("pages", config.default_pages())
    try:
        pages = int(pages)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="pages must be a whole number.") from None
    if pages < 1 or pages > config.MAX_PAGES:
        raise HTTPException(
            status_code=400, detail=f"pages must be between 1 and {config.MAX_PAGES}."
        )
    run = runs.start(idea, title, pages)
    logger.info("run %s started pages=%s", run.id, pages)
    return JSONResponse({"run_id": run.id, "book_id": run.book_id, "pages": pages})


@app.get("/api/runs/{run_id}/events")
async def run_events(run_id: str, request: Request) -> StreamingResponse:
    run = runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="That run is not in memory any more.")
    start = 0
    resume = request.headers.get("last-event-id") or request.query_params.get("from")
    if resume:
        try:
            start = int(resume) + 1
        except ValueError:
            start = 0

    async def stream():
        yield "retry: 2000\n\n"
        yield ": connected\n\n"
        async for event_id, event in run.follow(HEARTBEAT_SECONDS, start):
            yield _sse(event_id, event)

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


def _sse(event_id: int | None, event: dict) -> str:
    lines = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event['event']}")
    lines.append("data: " + json.dumps(event["data"], ensure_ascii=False))
    return "\n".join(lines) + "\n\n"


@app.post("/api/runs/{run_id}/stop")
async def stop_run(run_id: str) -> JSONResponse:
    run = runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="That run is not in memory any more.")
    run.request_stop()
    logger.info("run %s stopped by the reader after %s pages", run.id, run.pages_done)
    return JSONResponse({"stopped": True, "pages_kept": run.pages_done})


@app.get("/api/books")
async def api_books() -> JSONResponse:
    return JSONResponse({"books": store.recent()})


@app.get("/books", response_class=HTMLResponse)
async def books_page() -> HTMLResponse:
    return HTMLResponse(render.books_page(store.recent()))


@app.get("/b/{book_id}", include_in_schema=False)
async def book_redirect(book_id: str) -> RedirectResponse:
    return RedirectResponse(url=f"/b/{book_id}/", status_code=308)


@app.get("/b/{book_id}/", response_class=HTMLResponse)
async def book_page(book_id: str) -> HTMLResponse:
    book = store.load(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="No book with that address.")
    return HTMLResponse(render.book_page(book))


@app.get("/b/{book_id}/book.md")
async def book_markdown(book_id: str) -> FileResponse:
    path = store.markdown_path(book_id)
    if path is None:
        raise HTTPException(status_code=404, detail="No book with that address.")
    return FileResponse(path, media_type="text/markdown; charset=utf-8")
