import asyncio
import base64

import pytest

from app.core import build_flux_request, decode_image, parse_image_response, save_image_reference


def test_request_wraps_prompt_and_sets_flux_fields():
    body = build_flux_request("A robot holding a coffee cup")
    data = body["input"]
    assert data["width"] == 768
    assert data["height"] == 768
    assert data["guidance"] == 1.0
    assert data["image_format"] == "png"
    assert "die-cut sticker" in data["prompt"]
    assert "white border" in data["prompt"]
    assert data["prompt"].endswith("A robot holding a coffee cup")


def test_request_rejects_invalid_dimensions():
    with pytest.raises(ValueError, match="multiples of 64"):
        build_flux_request("test", 750, 768)


def test_parse_documented_url_response():
    parsed = parse_image_response({"status": "COMPLETED", "output": {"image_url": "https://image.runpod.ai/out.png"}})
    assert parsed.kind == "url"
    assert parsed.value.endswith("out.png")


def test_parse_and_decode_base64_response():
    encoded = base64.b64encode(b"png bytes").decode()
    parsed = parse_image_response({"status": "COMPLETED", "output": {"image_base64": encoded}})
    assert parsed.kind == "base64"
    assert decode_image(parsed.value) == b"png bytes"


def test_failed_response_surfaces_error():
    with pytest.raises(RuntimeError, match="out of memory"):
        parse_image_response({"status": "FAILED", "error": "out of memory"})


def test_parse_real_flux_result_url_and_save_jpeg_extension(tmp_path):
    payload = {
        "delayTime": 4913,
        "executionTime": 27212,
        "id": "sync-f77d96da-...",
        "status": "COMPLETED",
        "workerId": "4l1xq6pbsxoec6",
        "output": {
            "cost": 0.003,
            "result": "https://image.runpod.ai/wavespeed-flux-schnell/9151a30b.../result.jpeg",
        },
    }
    requested = []

    class FakeDownloadResponse:
        is_error = False
        status_code = 200
        text = ""
        content = b"\xff\xd8\xffjpeg bytes"
        headers = {"content-type": "image/jpeg"}

    async def fake_downloader(url):
        requested.append(url)
        return FakeDownloadResponse()

    parsed = parse_image_response(payload)
    path, _ = asyncio.run(save_image_reference(parsed, tmp_path, fake_downloader))

    assert parsed.value == payload["output"]["result"]
    assert parsed.cost == 0.003
    assert requested == [parsed.value]
    assert path.suffix == ".jpeg"
