"""Books on disk. One directory per book under DATA_DIR/books."""

import json
import logging
import os
import re
import secrets
import string
from dataclasses import dataclass
from pathlib import Path

from . import config
from .outline import Outline

ID_ALPHABET = string.ascii_lowercase + string.digits
ID_PATTERN = re.compile(r"^[a-z0-9]{10}$")
logger = logging.getLogger(__name__)


def new_id() -> str:
    return "".join(secrets.choice(ID_ALPHABET) for _ in range(10))


def valid_id(book_id: str) -> bool:
    return bool(ID_PATTERN.match(book_id or ""))


def book_dir(book_id: str) -> Path:
    return config.books_dir() / book_id


def data_dir_error() -> str:
    target = config.data_dir()
    return (
        f"DATA_DIR {target} is not writable. Create it on the host with "
        f"install -d -o 1000 -g 1000 {target}"
    )


def prepare() -> None:
    """Make the books directory and prove we can write to it."""
    books = config.books_dir()
    books.mkdir(parents=True, exist_ok=True)
    if not os.access(books, os.W_OK | os.X_OK):
        raise PermissionError(data_dir_error())


@dataclass
class Book:
    id: str
    meta: dict
    outline: dict
    pages: list[str]


def save(
    book_id: str,
    idea: str,
    outline: Outline,
    pages: list[str],
    meta: dict,
) -> None:
    target = book_dir(book_id)
    (target / "pages").mkdir(parents=True, exist_ok=True)
    for number, text in enumerate(pages, start=1):
        (target / "pages" / f"{number:04d}.md").write_text(text.strip() + "\n", encoding="utf-8")
    (target / "outline.json").write_text(
        json.dumps(outline.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (target / "book.md").write_text(_markdown(outline, pages, idea), encoding="utf-8")
    payload = dict(meta)
    payload.update({"id": book_id, "idea": idea, "title": outline.title, "pages": len(pages)})
    # meta.json is written last, so a directory without it is a book that never finished.
    (target / "meta.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _markdown(outline: Outline, pages: list[str], idea: str) -> str:
    lines = [f"# {outline.title}", "", f"Built from this idea: {idea}", ""]
    for chapter in outline.chapters:
        if chapter.first_page > len(pages):
            break
        lines += [f"## {chapter.number}. {chapter.title}", ""]
        for number in range(chapter.first_page, min(chapter.last_page, len(pages)) + 1):
            lines += [f"### Page {number}", "", pages[number - 1].strip(), ""]
    return "\n".join(lines) + "\n"


def load(book_id: str) -> Book | None:
    if not valid_id(book_id):
        return None
    target = book_dir(book_id)
    meta_path = target / "meta.json"
    if not meta_path.is_file():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        outline = json.loads((target / "outline.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.error("book %s is unreadable on disk", book_id)
        return None
    pages = [
        path.read_text(encoding="utf-8").strip()
        for path in sorted((target / "pages").glob("*.md"))
    ]
    return Book(id=book_id, meta=meta, outline=outline, pages=pages)


def markdown_path(book_id: str) -> Path | None:
    if not valid_id(book_id):
        return None
    path = book_dir(book_id) / "book.md"
    return path if path.is_file() else None


def recent(limit: int = 60) -> list[dict]:
    books = config.books_dir()
    if not books.is_dir():
        return []
    found: list[dict] = []
    for entry in books.iterdir():
        if not entry.is_dir() or not valid_id(entry.name):
            continue
        meta_path = entry / "meta.json"
        if not meta_path.is_file():
            continue
        try:
            found.append(json.loads(meta_path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    found.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    return found[:limit]
