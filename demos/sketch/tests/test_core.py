import asyncio
import base64
import io

import pytest
from PIL import Image

from app import core


def jpeg_bytes(width: int, height: int) -> bytes:
    image = Image.new("RGB", (width, height), (240, 240, 235))
    for x in range(0, width, 40):
        for y in range(0, height, 40):
            image.putpixel((x, y), (30, 30, 30))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_downscale_fits_the_long_side_and_re_encodes_as_jpeg():
    result = core.downscale_jpeg(jpeg_bytes(2400, 1200))

    with Image.open(io.BytesIO(result)) as image:
        assert image.format == "JPEG"
        assert image.size == (1280, 640)
    assert result.startswith(b"\xff\xd8\xff")


def test_downscale_leaves_a_small_image_at_its_own_size():
    with Image.open(io.BytesIO(core.downscale_jpeg(jpeg_bytes(640, 480)))) as image:
        assert image.size == (640, 480)


def test_downscale_rejects_bytes_that_are_not_an_image():
    with pytest.raises(ValueError, match="not a readable image"):
        core.downscale_jpeg(b"this is not an image")


def test_data_url_carries_the_jpeg_bytes():
    photo = core.downscale_jpeg(jpeg_bytes(800, 600))
    url = core.jpeg_data_url(photo)

    assert url.startswith("data:image/jpeg;base64,")
    assert base64.b64decode(url.split(",", 1)[1]) == photo


def test_request_sends_the_notes_and_the_data_url_as_two_content_parts(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "Qwen/Qwen2.5-VL-7B-Instruct")
    body = core.build_chat_request("data:image/jpeg;base64,AAAA", "Call it Ada's Garage")
    content = body["messages"][1]["content"]

    assert body["model"] == "Qwen/Qwen2.5-VL-7B-Instruct"
    assert body["stream"] is True
    assert body["messages"][0]["role"] == "system"
    assert "one complete HTML document" in body["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": "Call it Ada's Garage"}
    assert content[1] == {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,AAAA"}}


def test_request_without_notes_still_asks_for_the_page():
    content = core.build_chat_request("data:image/jpeg;base64,AAAA")["messages"][1]["content"]

    assert content[0]["text"] == "Build the page in this sketch."


def test_extract_html_from_a_fenced_reply():
    document = "<!doctype html>\n<html><body><h1>Header</h1></body></html>"

    assert core.extract_html(f"Here you go:\n```html\n{document}\n```") == document


def test_extract_html_from_an_unfenced_reply_with_prose_around_it():
    document = "<html><head><style>h1{color:red}</style></head><body><h1>Header</h1></body></html>"

    assert core.extract_html(f"Sure.\n{document}\nThat matches the sketch.") == document


def test_extract_html_keeps_everything_up_to_the_last_closing_tag():
    document = "<!DOCTYPE html><html><body><p>a</p><!-- </html> --><p>b</p></body></html>"

    assert core.extract_html(document) == document


def test_extract_html_rejects_a_reply_without_a_document():
    with pytest.raises(RuntimeError, match="complete HTML document"):
        core.extract_html("I cannot read the photograph.")


def test_base_url_defaults_to_the_runpod_endpoint(monkeypatch):
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.setenv("RUNPOD_ENDPOINT_ID", "abc123")

    assert core.llm_base_url() == "https://api.runpod.ai/v2/abc123/openai/v1"


def test_base_url_requires_configuration(monkeypatch):
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("RUNPOD_ENDPOINT_ID", raising=False)

    with pytest.raises(RuntimeError, match="LLM_BASE_URL or RUNPOD_ENDPOINT_ID"):
        core.llm_base_url()


def collect(usage: dict | None = None) -> list[str]:
    async def run():
        return [token async for token in core.stream_page("data:image/jpeg;base64,AAAA", "", usage)]

    return asyncio.run(run())


def test_stream_reads_openai_compatible_events(monkeypatch, fake_upstream):
    fake_upstream(monkeypatch)

    assert collect() == ["<!doctype html>", "<html></html>"]


def test_stream_tolerates_a_usage_only_final_chunk(monkeypatch, fake_upstream):
    fake_upstream(
        monkeypatch,
        events=(
            '{"choices":[{"delta":{"content":"<!doctype html>"}}]}',
            '{"choices":[{"delta":{"content":"<html></html>"},"finish_reason":"stop"}]}',
            '{"id":"chatcmpl-1","object":"chat.completion.chunk","model":"Qwen/Qwen2.5-VL-7B-Instruct",'
            '"choices":[],"usage":{"prompt_tokens":1200,"completion_tokens":300,"total_tokens":1500}}',
            "[DONE]",
        ),
    )
    usage: dict = {}

    assert collect(usage) == ["<!doctype html>", "<html></html>"]
    assert usage["total_tokens"] == 1500


def test_stream_passes_a_402_body_through_unchanged(monkeypatch, fake_upstream):
    body = '{"status":402,"title":"Insufficient Balance","detail":"insufficient balance"}'
    fake_upstream(monkeypatch, fail_status=402, fail_body=body)

    with pytest.raises(RuntimeError, match="RunPod returned HTTP 402: " + r"\{"):
        collect()


def test_stream_passes_a_401_body_through_unchanged(monkeypatch, fake_upstream):
    fake_upstream(monkeypatch, fail_status=401, fail_body="Unauthorized: invalid API key")

    with pytest.raises(RuntimeError, match="RunPod returned HTTP 401: Unauthorized: invalid API key"):
        collect()


def test_stream_requires_an_api_key(monkeypatch):
    monkeypatch.delenv("RUNPOD_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="RUNPOD_API_KEY is not set"):
        collect()
