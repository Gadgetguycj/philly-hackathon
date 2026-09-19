"""Every setting the app reads. Nothing outside this module touches os.environ."""

import os
from pathlib import Path

DEFAULT_BASE_URL = "https://api.runpod.ai/v2/moonshot-kimi/openai/v1"
DEFAULT_MODEL = "kimi-k2.6"
DEFAULT_PAGES = 100
PAGE_CHOICES = (10, 25, 50, 100)
# A sanity bound on one request, not a quota. There is no hourly or per IP limit anywhere.
MAX_PAGES = 1000


def api_key() -> str:
    return os.getenv("RUNPOD_API_KEY", "").strip()


def base_url() -> str:
    return (os.getenv("LLM_BASE_URL") or DEFAULT_BASE_URL).strip().rstrip("/")


def model() -> str:
    return (os.getenv("LLM_MODEL") or DEFAULT_MODEL).strip()


def default_pages() -> int:
    raw = (os.getenv("BOOK_PAGES") or "").strip()
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_PAGES
    if value < 1 or value > MAX_PAGES:
        return DEFAULT_PAGES
    return value


def page_choices() -> list[int]:
    """The selector options, with BOOK_PAGES added when it is not one of the four."""
    choices = set(PAGE_CHOICES)
    choices.add(default_pages())
    return sorted(choices)


def data_dir() -> Path:
    return Path(os.getenv("DATA_DIR") or "/data")


def books_dir() -> Path:
    return data_dir() / "books"
