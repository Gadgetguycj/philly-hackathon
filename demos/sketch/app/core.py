import base64
import io
import json
import logging
import os
from collections.abc import AsyncIterator

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger(__name__)

MAX_IMAGE_EDGE = 1280
JPEG_QUALITY = 85
MAX_NOTES_CHARS = 600

SYSTEM_PROMPT = (
    "You read a photograph of a hand-drawn website sketch and write the page it describes. "
    "Answer with one complete HTML document and nothing else. "
    "Start with <!doctype html> and end with </html>. "
    "Put every style rule in a single <style> element inside <head>. "
    "Use no images, no fonts, no stylesheets, no scripts, and no requests to any other site. "
    "Keep the layout of the sketch: the same sections, in the same order, with the same columns. "
    "Copy the words written in the sketch. Where a box has no label, write one short line that fits the drawing."
)


def downscale_jpeg(data: bytes, max_edge: int = MAX_IMAGE_EDGE, quality: int = JPEG_QUALITY) -> bytes:
    try:
        with Image.open(io.BytesIO(data)) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("The upload was not a readable image.") from exc
    width, height = image.size
    longest = max(width, height)
    if longest > max_edge:
        scale = max_edge / longest
        image = image.resize((max(round(width * scale), 1), max(round(height * scale), 1)), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()


def jpeg_data_url(jpeg_bytes: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(jpeg_bytes).decode()


def llm_model() -> str:
    return os.getenv("LLM_MODEL", "").strip() or "Qwen/Qwen2.5-VL-7B-Instruct"


def llm_base_url() -> str:
    configured = os.getenv("LLM_BASE_URL", "").strip().rstrip("/")
    if configured:
        return configured
    endpoint_id = os.getenv("RUNPOD_ENDPOINT_ID", "").strip()
    if endpoint_id:
        return f"https://api.runpod.ai/v2/{endpoint_id}/openai/v1"
    raise RuntimeError("Set LLM_BASE_URL or RUNPOD_ENDPOINT_ID before building a page.")


def build_chat_request(data_url: str, notes: str = "") -> dict:
    text = notes.strip()[:MAX_NOTES_CHARS] or "Build the page in this sketch."
    return {
        "model": llm_model(),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
        "temperature": 0.3,
        "max_tokens": 4_000,
        "stream": True,
    }


def request_timeout() -> float:
    try:
        seconds = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "900"))
    except ValueError:
        return 900.0
    return seconds if seconds > 0 else 900.0


def keepalive_interval() -> float:
    try:
        seconds = float(os.getenv("KEEPALIVE_INTERVAL_SECONDS", "10"))
    except ValueError:
        return 10.0
    return seconds if seconds > 0 else 10.0


def extract_html(text: str) -> str:
    body = text.strip()
    lower = body.lower()
    starts = [index for index in (lower.find("<!doctype"), lower.find("<html")) if index >= 0]
    end = lower.rfind("</html>")
    if not starts or end < 0:
        raise RuntimeError("The model did not return a complete HTML document.")
    start = min(starts)
    if end < start:
        raise RuntimeError("The model did not return a complete HTML document.")
    return body[start : end + len("</html>")].strip()


async def stream_page(data_url: str, notes: str = "", usage: dict | None = None) -> AsyncIterator[str]:
    api_key = os.getenv("RUNPOD_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("RUNPOD_API_KEY is not set.")
    url = f"{llm_base_url()}/chat/completions"
    timeout = httpx.Timeout(request_timeout(), connect=20.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST",
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=build_chat_request(data_url, notes),
        ) as response:
            if response.is_error:
                body = (await response.aread()).decode(errors="replace")
                raise RuntimeError(f"RunPod returned HTTP {response.status_code}: {body}")
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                if not data:
                    continue
                try:
                    parsed = json.loads(data)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(f"RunPod returned an invalid stream event: {data}") from exc
                if not isinstance(parsed, dict):
                    continue
                reported = parsed.get("usage")
                if isinstance(reported, dict) and usage is not None:
                    usage.update(reported)
                choices = parsed.get("choices")
                if choices == []:
                    logger.info("RunPod stream usage: %s", reported)
                    continue
                if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
                    continue
                choice = choices[0]
                delta = choice.get("delta")
                if isinstance(delta, dict):
                    token = delta.get("content")
                    if token:
                        yield token
