"""Streaming client for any OpenAI compatible /chat/completions endpoint."""

import json
import re
from contextlib import aclosing
from typing import AsyncIterator, Callable

import httpx

from . import config

# Long enough for a cold serverless endpoint to wake up. The event stream heartbeats
# while this wait is happening, so no proxy in front of us sees a quiet connection.
TIMEOUT = httpx.Timeout(connect=20.0, read=600.0, write=60.0, pool=60.0)
BODY_EXCERPT_CHARS = 600
_BEARER = re.compile(r"(?i)bearer\s+\S+")
_RUNPOD_KEY = re.compile(r"rpa_[A-Za-z0-9]{8,}")


def redact(text: str) -> str:
    """Remove the API key from anything that may reach a browser or a log."""
    if not text:
        return ""
    key = config.api_key()
    if len(key) >= 6:
        text = text.replace(key, "[redacted]")
    text = _BEARER.sub("Bearer [redacted]", text)
    return _RUNPOD_KEY.sub("[redacted]", text)


class UpstreamError(Exception):
    """An error from the model endpoint, already redacted and ready to show."""

    def __init__(self, status: int, message: str, body: str = "") -> None:
        self.status = status
        self.body = redact(body)[:BODY_EXCERPT_CHARS]
        text = redact(message)
        if self.body:
            text = f"{text} Upstream said: {self.body}"
        super().__init__(text)
        self.message = text


def _explain(status: int) -> str:
    if status == 401 or status == 403:
        return "The endpoint rejected the API key. RUNPOD_API_KEY is wrong or not allowed on this endpoint."
    if status == 402:
        return "The RunPod account has no credit, so the endpoint will not run."
    if status == 404:
        return f"The endpoint or the model was not found at {config.base_url()}. Check LLM_BASE_URL and LLM_MODEL."
    if status == 429:
        return "The endpoint is rate limiting us. This app sets no limits of its own."
    if status >= 500:
        return f"The endpoint returned {status}."
    return f"The endpoint returned {status}."


def build_client() -> httpx.AsyncClient:
    key = config.api_key()
    headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    return httpx.AsyncClient(base_url=config.base_url(), headers=headers, timeout=TIMEOUT)


def _payload(messages: list[dict], max_tokens: int, temperature: float) -> dict:
    # stream_options is deliberately not sent. Usage is not needed for the counters, and
    # some OpenAI compatible servers reject the field. A usage only chunk is still handled.
    body = {
        "model": config.model(),
        "messages": messages,
        "stream": True,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    # LLM_EXTRA carries whatever the endpoint in front of us needs, such as the switch that
    # turns a reasoning model's thinking off. It is merged last, so it can also replace a
    # field above.
    body.update(config.llm_extra())
    return body


def reasoning_tokens(usage: object) -> int | None:
    """The reasoning token count from one usage object, or None if it does not carry one."""
    if not isinstance(usage, dict):
        return None
    details = usage.get("completion_tokens_details")
    if not isinstance(details, dict):
        return None
    value = details.get("reasoning_tokens")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


async def stream_chat(
    client: httpx.AsyncClient,
    messages: list[dict],
    max_tokens: int = 1600,
    temperature: float = 0.8,
) -> AsyncIterator[tuple[str, object]]:
    """Yield ("delta", text), ("finish", reason) and ("usage", dict) as they arrive."""
    body = _payload(messages, max_tokens, temperature)
    try:
        async with client.stream("POST", "/chat/completions", json=body) as response:
            if response.status_code != 200:
                raw = await response.aread()
                raise UpstreamError(
                    response.status_code,
                    _explain(response.status_code),
                    raw.decode("utf-8", "replace"),
                )
            async for line in response.aiter_lines():
                for item in _parse_line(line):
                    yield item
    except httpx.HTTPError as error:
        raise UpstreamError(0, f"Could not reach {config.base_url()}: {type(error).__name__}", str(error)) from None


def _parse_line(line: str) -> list[tuple[str, object]]:
    line = line.strip()
    if not line or line.startswith(":") or not line.startswith("data:"):
        return []
    data = line[len("data:") :].strip()
    if not data or data == "[DONE]":
        return []
    try:
        chunk = json.loads(data)
    except json.JSONDecodeError:
        return []
    if not isinstance(chunk, dict):
        return []
    if isinstance(chunk.get("error"), dict):
        message = chunk["error"].get("message") or "The endpoint reported an error mid stream."
        raise UpstreamError(200, str(message))
    out: list[tuple[str, object]] = []
    usage = chunk.get("usage")
    choices = chunk.get("choices")
    # A usage only final chunk carries an empty choices list, or no choices key at all.
    if isinstance(choices, list):
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            delta = choice.get("delta")
            if isinstance(delta, dict):
                # Only content is read. A reasoning model also sends its thinking, as
                # reasoning_content on Kimi and as reasoning on vLLM. Thinking is never
                # part of a page, so no other field of the delta is touched.
                text = delta.get("content")
                if isinstance(text, str) and text:
                    out.append(("delta", text))
            reason = choice.get("finish_reason")
            if isinstance(reason, str) and reason:
                out.append(("finish", reason))
    if isinstance(usage, dict):
        out.append(("usage", usage))
    return out


async def complete(
    client: httpx.AsyncClient,
    messages: list[dict],
    max_tokens: int = 1600,
    on_usage: Callable[[object], None] | None = None,
) -> str:
    """Collect a whole streamed reply into one string. Reasoning content is not part of it."""
    parts: list[str] = []
    async with aclosing(
        stream_chat(client, messages, max_tokens=max_tokens, temperature=0.4)
    ) as tokens:
        async for kind, value in tokens:
            if kind == "delta":
                parts.append(str(value))
            elif kind == "usage" and on_usage is not None:
                on_usage(value)
    return "".join(parts)
