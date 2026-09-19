"""Every setting the app reads. Nothing outside this module touches os.environ."""

import json
import logging
import os
from pathlib import Path

DEFAULT_BASE_URL = "https://api.runpod.ai/v2/moonshot-kimi/openai/v1"
DEFAULT_MODEL = "kimi-k2.6"
DEFAULT_PAGES = 30
PAGE_CHOICES = (10, 20, 30)
# A sanity bound on one request, not a quota. There is no hourly or per IP limit anywhere.
MAX_PAGES = 30
logger = logging.getLogger(__name__)


def api_key() -> str:
    return os.getenv("RUNPOD_API_KEY", "").strip()


def base_url() -> str:
    return (os.getenv("LLM_BASE_URL") or DEFAULT_BASE_URL).strip().rstrip("/")


def model() -> str:
    return (os.getenv("LLM_MODEL") or DEFAULT_MODEL).strip()


def llm_extra() -> dict:
    """Extra top level fields for the chat completions body, as a JSON object.

    Reasoning models are switched off by a field this app does not name: Kimi on RunPod
    takes {"thinking": {"type": "disabled"}}, gpt-oss on vLLM takes
    {"reasoning_effort": "low"}. The default is empty, so the app stays vendor neutral.
    """
    raw = (os.getenv("LLM_EXTRA") or "").strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        _warn_once(raw, f"LLM_EXTRA is not valid JSON ({error.msg} at position {error.pos}), so it is ignored.")
        return {}
    if not isinstance(value, dict):
        _warn_once(raw, "LLM_EXTRA is not a JSON object, so it is ignored.")
        return {}
    return value


_warned: set[str] = set()


def _warn_once(raw: str, message: str) -> None:
    """Complain about a bad LLM_EXTRA once per value, not once per request."""
    if raw in _warned:
        return
    _warned.add(raw)
    logger.warning("%s", message)


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
