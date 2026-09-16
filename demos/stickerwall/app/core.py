import base64
import binascii
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable
from urllib.parse import unquote, urlsplit
from uuid import uuid4

import httpx


@dataclass(frozen=True)
class ImageReference:
    kind: str
    value: str
    cost: float | None = None


@dataclass(frozen=True)
class SavedGeneration:
    http_status: int
    response_shape: str
    bytes_written: int
    path: Path
    cost: float | None = None


def sticker_prompt(prompt: str) -> str:
    return (
        "A die-cut sticker with a clean white border, flat colors, centered subject, "
        f"plain background. {prompt.strip()}"
    )


def build_flux_request(prompt: str, width: int = 768, height: int = 768) -> dict:
    if width % 64 or height % 64:
        raise ValueError("Image width and height must be multiples of 64.")
    return {
        "input": {
            "prompt": sticker_prompt(prompt),
            "width": width,
            "height": height,
            "num_inference_steps": 4,
            "guidance": 1.0,
            "seed": -1,
            "image_format": "png",
        }
    }


def _cost(output: dict) -> float | None:
    value = output.get("cost")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _is_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def _looks_like_base64(value: str) -> bool:
    if value.startswith("data:"):
        return True
    if len(value) < 64 or "/" in value:
        return False
    try:
        return bool(base64.b64decode(value, validate=True))
    except (binascii.Error, ValueError):
        return False


def _reference(value: object, cost: float | None) -> ImageReference | None:
    if not isinstance(value, str) or not value:
        return None
    if _is_url(value):
        return ImageReference("url", value, cost)
    if _looks_like_base64(value):
        return ImageReference("base64", value, cost)
    return None


def parse_image_response(payload: dict) -> ImageReference:
    if payload.get("status") != "COMPLETED":
        error = payload.get("error")
        output = payload.get("output")
        if error is None and isinstance(output, dict):
            error = output.get("error")
        raise RuntimeError(str(error if error is not None else payload))

    output = payload.get("output")
    if isinstance(output, dict):
        cost = _cost(output)
        result = output.get("result")
        if isinstance(result, str) and _is_url(result):
            return ImageReference("url", result, cost)

        reference = _reference(output.get("image_url"), cost)
        if reference:
            return reference

        images = output.get("images")
        if isinstance(images, list) and images:
            reference = _reference(images[0], cost)
            if reference:
                return reference

        reference = _reference(output.get("image"), cost)
        if reference:
            return reference

    reference = _reference(payload.get("image_url"), _cost(output) if isinstance(output, dict) else None)
    if reference:
        return reference

    # Retain support for older RunPod response fields after the documented fields.
    if isinstance(output, dict):
        cost = _cost(output)
        for key in ("image_base64", "base64"):
            value = output.get(key)
            if isinstance(value, str) and value:
                return ImageReference("base64", value, cost)
    reference = _reference(output, None)
    if reference:
        return reference
    raise RuntimeError(f"RunPod response did not contain an image: {payload}")


def decode_image(value: str) -> bytes:
    encoded = value.split(",", 1)[1] if value.startswith("data:") and "," in value else value
    try:
        return base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise RuntimeError("RunPod returned invalid base64 image data.") from exc


def _content_type_extension(content_type: str) -> str | None:
    return {
        "image/jpeg": ".jpeg",
        "image/jpg": ".jpeg",
        "image/png": ".png",
    }.get(content_type.partition(";")[0].strip().lower())


def _url_extension(url: str) -> str | None:
    suffix = Path(unquote(urlsplit(url).path)).suffix.lower()
    return suffix if suffix and suffix[1:].isalnum() else None


def _base64_extension(value: str, image_bytes: bytes) -> str:
    if value.startswith("data:"):
        media_type = value[5:].partition(";")[0]
        extension = _content_type_extension(media_type)
        if extension:
            return extension
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return ".jpeg"
    return ".png"


async def save_image_reference(
    reference: ImageReference,
    output_dir: Path,
    downloader: Callable[[str], Awaitable[httpx.Response]],
) -> tuple[Path, int]:
    if reference.kind == "url":
        image_response = await downloader(reference.value)
        if image_response.is_error:
            raise RuntimeError(f"Image download returned HTTP {image_response.status_code}: {image_response.text}")
        image_bytes = image_response.content
        extension = _url_extension(reference.value)
        if extension is None:
            extension = _content_type_extension(image_response.headers.get("content-type", ""))
        if extension is None:
            raise RuntimeError("Downloaded image had no recognized file extension or Content-Type.")
    else:
        image_bytes = decode_image(reference.value)
        extension = _base64_extension(reference.value, image_bytes)

    if not image_bytes:
        raise RuntimeError("RunPod returned an empty image.")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{uuid4().hex}{extension}"
    path.write_bytes(image_bytes)
    return path, len(image_bytes)


async def generate_sticker(prompt: str, output_dir: Path, width: int = 768, height: int = 768) -> SavedGeneration:
    api_key = os.getenv("RUNPOD_API_KEY", "")
    if not api_key:
        raise RuntimeError("RUNPOD_API_KEY is not set.")
    model = os.getenv("FLUX_MODEL", "black-forest-labs-flux-1-schnell")
    url = f"https://api.runpod.ai/v2/{model}/runsync"
    timeout = httpx.Timeout(180.0, connect=20.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=build_flux_request(prompt, width, height),
        )
        if response.is_error:
            raise RuntimeError(f"RunPod returned HTTP {response.status_code}: {response.text}")
        try:
            reference = parse_image_response(response.json())
        except ValueError as exc:
            raise RuntimeError(f"RunPod returned invalid JSON: {response.text}") from exc
        path, bytes_written = await save_image_reference(reference, output_dir, client.get)
    return SavedGeneration(response.status_code, reference.kind, bytes_written, path, reference.cost)
