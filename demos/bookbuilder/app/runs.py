"""One book build: the outline, then the pages, then the saved book.

Pages are generated with up to three requests in flight and are always emitted in page
order. See CONCURRENCY in the README for how continuity survives that.
"""

import asyncio
import logging
import time
from contextlib import aclosing
from datetime import datetime, timezone
from typing import AsyncIterator

import httpx

from . import config, llm, outline as outline_mod, pages as pages_mod, store
from .outline import Chapter, Outline

MAX_IN_FLIGHT = 3
OUTLINE_MAX_TOKENS = 2000
RAW_REPLY_CHARS = 1500
KEEP_FINISHED_RUNS = 20
logger = logging.getLogger(__name__)


class OutlineFailed(Exception):
    """The model would not return the outline shape, twice."""

    def __init__(self, message: str, raw: str) -> None:
        super().__init__(message)
        self.raw = llm.redact(raw)[:RAW_REPLY_CHARS]


class PageStream:
    """The tokens of one page. Written by a worker, read once by the emitter."""

    def __init__(self, index: int, chapter: Chapter) -> None:
        self.index = index
        self.chapter = chapter
        self.chunks: list[str] = []
        self.done = False
        self.error: str | None = None
        self.truncated = False
        self.first_token_ms: int | None = None
        self.started_ms = 0
        self.elapsed_ms = 0
        self._ready = asyncio.Event()

    @property
    def text(self) -> str:
        return "".join(self.chunks)

    def push(self, text: str) -> None:
        self.chunks.append(text)
        self._ready.set()

    def close(self, error: str | None = None) -> None:
        self.error = error
        self.done = True
        self._ready.set()

    async def follow(self) -> AsyncIterator[str]:
        position = 0
        while True:
            if position < len(self.chunks):
                batch = self.chunks[position:]
                position = len(self.chunks)
                # One event per group. A page that was written ahead of its turn replays
                # in a single event instead of a hundred.
                yield "".join(batch)
                continue
            if self.done:
                return
            self._ready.clear()
            if position < len(self.chunks) or self.done:
                continue
            await self._ready.wait()


class Run:
    def __init__(self, idea: str, title: str, pages_requested: int) -> None:
        self.id = store.new_id()
        self.book_id = store.new_id()
        self.idea = idea
        self.requested_title = title
        self.pages_requested = pages_requested
        self.outline: Outline | None = None
        self.events: list[dict] = []
        self.waiters: set[asyncio.Event] = set()
        self.streams: dict[int, PageStream] = {}
        self.workers: list[asyncio.Task] = []
        self.task: asyncio.Task | None = None
        self.failure: Exception | None = None
        self.stopped = False
        self.finished = False
        self.words = 0
        self.pages_done = 0
        self.kept: list[str] = []
        self.created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.started = time.monotonic()
        self._stream_ready = asyncio.Event()

    # Bookkeeping -----------------------------------------------------------

    def elapsed(self) -> float:
        return time.monotonic() - self.started

    def words_per_second(self) -> float:
        seconds = self.elapsed()
        return round(self.words / seconds, 1) if seconds > 0.05 else 0.0

    @property
    def halting(self) -> bool:
        return self.stopped or self.failure is not None

    def emit(self, kind: str, **data: object) -> None:
        self.events.append({"event": kind, "data": data})
        for waiter in self.waiters:
            waiter.set()

    def finish(self) -> None:
        self.finished = True
        for waiter in self.waiters:
            waiter.set()

    def add_stream(self, index: int, stream: PageStream) -> None:
        self.streams[index] = stream
        self._stream_ready.set()

    def fail(self, error: Exception) -> None:
        if self.failure is None:
            self.failure = error
        self._stream_ready.set()

    def request_stop(self) -> None:
        """Cancel the requests in flight and keep the pages that finished."""
        if self.finished:
            return
        self.stopped = True
        self._stream_ready.set()
        self.emit("status", phase="stopping", message="Stopping. The finished pages are kept.")
        for worker in self.workers:
            worker.cancel()

    async def wait_for_stream(self, index: int) -> PageStream | None:
        while index not in self.streams:
            if self.halting:
                return None
            self._stream_ready.clear()
            if index in self.streams or self.halting:
                continue
            await self._stream_ready.wait()
        return self.streams[index]

    async def follow(
        self, heartbeat_seconds: float, start: int = 0
    ) -> AsyncIterator[tuple[int | None, dict]]:
        """Yield (event id, event) from start onwards. A heartbeat has no event id."""
        waiter = asyncio.Event()
        self.waiters.add(waiter)
        try:
            position = max(0, start)
            while True:
                if position < len(self.events):
                    batch = self.events[position:]
                    for offset, event in enumerate(batch, start=position):
                        yield offset, event
                    position += len(batch)
                    continue
                if self.finished:
                    return
                waiter.clear()
                if position < len(self.events) or self.finished:
                    continue
                try:
                    await asyncio.wait_for(waiter.wait(), heartbeat_seconds)
                except asyncio.TimeoutError:
                    yield None, {
                        "event": "heartbeat",
                        "data": {"seconds": round(self.elapsed(), 1)},
                    }
        finally:
            self.waiters.discard(waiter)


# The run registry -----------------------------------------------------------

RUNS: dict[str, Run] = {}


def start(idea: str, title: str, pages_requested: int) -> Run:
    _prune()
    run = Run(idea, title, pages_requested)
    RUNS[run.id] = run
    run.emit("run", id=run.id, book_id=run.book_id, pages=pages_requested, model=config.model())
    run.task = asyncio.create_task(execute(run))
    return run


def get(run_id: str) -> Run | None:
    return RUNS.get(run_id)


def _prune() -> None:
    finished = [run for run in RUNS.values() if run.finished]
    if len(finished) <= KEEP_FINISHED_RUNS:
        return
    finished.sort(key=lambda run: run.created_at)
    for run in finished[: len(finished) - KEEP_FINISHED_RUNS]:
        RUNS.pop(run.id, None)


# The build ------------------------------------------------------------------


async def execute(run: Run) -> None:
    try:
        if not config.api_key():
            raise llm.UpstreamError(0, "RUNPOD_API_KEY is not set, so there is no way to reach the model.")
        async with llm.build_client() as client:
            run.emit("status", phase="outline", message="Planning the chapters")
            run.outline = await make_outline(run, client)
            run.emit(
                "outline",
                title=run.outline.title,
                pages=run.outline.total_pages,
                chapters=[
                    {
                        "number": c.number,
                        "title": c.title,
                        "summary": c.summary,
                        "first_page": c.first_page,
                        "last_page": c.last_page,
                    }
                    for c in run.outline.chapters
                ],
            )
            run.emit("status", phase="writing", message="Writing page 1")
            await write_pages(run, client)
    except OutlineFailed as error:
        run.emit("failed", message=str(error), raw=error.raw)
    except llm.UpstreamError as error:
        run.emit("failed", message=error.message, status=error.status)
    except asyncio.CancelledError:
        run.stopped = True
        run.emit("status", phase="stopping", message="The run was cancelled.")
    except Exception as error:  # noqa: BLE001 - the browser gets the redacted reason
        logger.exception("run %s failed", run.id)
        run.emit("failed", message=llm.redact(f"{type(error).__name__}: {error}"))
    finally:
        _complete(run)


def _complete(run: Run) -> None:
    url = ""
    if run.kept and run.outline is not None:
        try:
            store.save(
                run.book_id,
                run.idea,
                run.outline,
                run.kept,
                {
                    "created_at": run.created_at,
                    "model": config.model(),
                    "pages_requested": run.pages_requested,
                    "stopped": run.stopped,
                    "words": run.words,
                    "seconds": round(run.elapsed(), 1),
                    "words_per_second": run.words_per_second(),
                },
            )
            url = f"/b/{run.book_id}/"
        except OSError:
            logger.error("%s", store.data_dir_error())
            run.emit("failed", message=store.data_dir_error())
    run.emit(
        "done",
        book_id=run.book_id if url else "",
        url=url,
        pages=len(run.kept),
        pages_requested=run.pages_requested,
        words=run.words,
        seconds=round(run.elapsed(), 1),
        words_per_second=run.words_per_second(),
        stopped=run.stopped,
    )
    run.finish()


async def make_outline(run: Run, client: httpx.AsyncClient) -> Outline:
    raw = ""
    for firmer in (False, True):
        messages = outline_mod.messages(run.idea, run.requested_title, run.pages_requested, firmer)
        raw = await llm.complete(client, messages, max_tokens=OUTLINE_MAX_TOKENS)
        try:
            return outline_mod.parse(raw, run.pages_requested, run.requested_title)
        except outline_mod.OutlineError as error:
            if firmer:
                raise OutlineFailed(
                    f"The model did not return an outline in the shape this app asked for, twice. {error}",
                    raw,
                ) from None
            run.emit(
                "status",
                phase="outline",
                message="The outline did not parse. Asking once more.",
            )
    raise OutlineFailed("The outline could not be built.", raw)


async def write_pages(run: Run, client: httpx.AsyncClient) -> None:
    outline = run.outline
    assert outline is not None
    limit = asyncio.Semaphore(MAX_IN_FLIGHT)
    previous_chapters = [None] + outline.chapters[:-1]
    run.workers = [
        asyncio.create_task(
            chapter_worker(run, client, chapter, before, limit),
            name=f"chapter-{chapter.number}",
        )
        for chapter, before in zip(outline.chapters, previous_chapters)
    ]
    try:
        await emit_pages(run, outline.total_pages)
    finally:
        for worker in run.workers:
            worker.cancel()
        await asyncio.gather(*run.workers, return_exceptions=True)
    if run.failure is not None:
        raise run.failure


async def emit_pages(run: Run, total: int) -> None:
    """Send the pages to the browser in page order, whatever order they were written in."""
    index = 1
    while index <= total:
        stream = await run.wait_for_stream(index)
        if stream is None:
            break
        run.emit(
            "page_start",
            index=index,
            total=total,
            chapter=stream.chapter.number,
            chapter_title=stream.chapter.title,
        )
        async for chunk in stream.follow():
            run.emit("delta", index=index, text=chunk)
        text = stream.text.strip()
        if stream.error is not None or not text:
            run.emit("page_dropped", index=index, reason=stream.error or "The model sent no text.")
            break
        run.kept.append(text)
        run.pages_done = index
        run.words += pages_mod.word_count(text)
        run.emit(
            "page_done",
            index=index,
            total=total,
            words=pages_mod.word_count(text),
            truncated=stream.truncated,
            first_token_ms=stream.first_token_ms,
            started_ms=stream.started_ms,
            elapsed_ms=stream.elapsed_ms,
            total_words=run.words,
            seconds=round(run.elapsed(), 1),
            words_per_second=run.words_per_second(),
        )
        index += 1
        if index <= total and not run.halting:
            run.emit("status", phase="writing", message=f"Writing page {index}")


async def chapter_worker(
    run: Run,
    client: httpx.AsyncClient,
    chapter: Chapter,
    before: Chapter | None,
    limit: asyncio.Semaphore,
) -> None:
    """Write one chapter, page by page. Pages inside a chapter are never parallel."""
    async with limit:
        previous = ""
        older = ""
        for page in range(chapter.first_page, chapter.last_page + 1):
            if run.halting:
                return
            stream = PageStream(page, chapter)
            run.add_stream(page, stream)
            recap = pages_mod.rolling_context(previous, older)
            messages = pages_mod.messages(run.outline, chapter, page, run.idea, recap, before)
            if not await _write_page(run, client, stream, messages, page):
                return
            older, previous = previous, stream.text


async def _write_page(
    run: Run,
    client: httpx.AsyncClient,
    stream: PageStream,
    messages: list[dict],
    page: int,
) -> bool:
    attempts = 0
    while True:
        started = time.monotonic()
        stream.started_ms = int((started - run.started) * 1000)
        try:
            # aclosing shuts the upstream request down the moment this page is cancelled.
            async with aclosing(
                llm.stream_chat(client, messages, max_tokens=pages_mod.MAX_TOKENS)
            ) as tokens:
                async for kind, value in tokens:
                    if kind == "delta":
                        if stream.first_token_ms is None:
                            stream.first_token_ms = int((time.monotonic() - started) * 1000)
                        stream.push(str(value))
                    elif kind == "finish" and value == "length":
                        # The page filled its token budget. Keep what arrived.
                        stream.truncated = True
        except asyncio.CancelledError:
            stream.close(error="The run was stopped before this page finished.")
            raise
        except llm.UpstreamError as error:
            retryable = error.status == 0 or error.status >= 500
            if attempts == 0 and retryable and not stream.chunks:
                attempts = 1
                run.emit("status", phase="writing", message=f"Page {page} did not start. Trying once more.")
                await asyncio.sleep(1.0)
                continue
            stream.close(error=error.message)
            run.fail(error)
            return False
        except Exception as error:  # noqa: BLE001
            logger.exception("page %s failed", page)
            wrapped = RuntimeError(llm.redact(f"{type(error).__name__}: {error}"))
            stream.close(error=str(wrapped))
            run.fail(wrapped)
            return False
        stream.elapsed_ms = int((time.monotonic() - started) * 1000)
        stream.close()
        return True
