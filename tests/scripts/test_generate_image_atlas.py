"""Contract tests for the Atlas Cloud image provider."""

from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import generate_image  # noqa: E402


def _png(width: int = 16, height: int = 16) -> bytes:
    """Build a real, fully valid greyscale PNG.

    generate_image.py validates provider output with _validate_png, which
    checks every chunk CRC and decompresses the IDAT stream, so a header stub
    is not enough here.
    """

    def _chunk(kind: bytes, data: bytes) -> bytes:
        return (
            len(data).to_bytes(4, "big")
            + kind
            + data
            + (zlib.crc32(kind + data) & 0xFFFFFFFF).to_bytes(4, "big")
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    raster = b"".join(b"\x00" + b"\x80" * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(raster))
        + _chunk(b"IEND", b"")
    )


class FakeResponse:
    def __init__(self, status_code=200, payload=None, body=b"", headers=None):
        self.status_code = status_code
        self._payload = payload
        self._body = body
        self.headers = headers or {}
        self.closed = False

    def json(self):
        return self._payload

    def iter_content(self, chunk_size):
        del chunk_size
        yield self._body

    def close(self):
        self.closed = True


def test_atlas_submits_once_polls_and_downloads_without_credentials(monkeypatch):
    calls = []
    responses = iter(
        [
            FakeResponse(payload={"data": {"id": "prediction-1", "status": "created"}}),
            FakeResponse(payload={"data": {"status": "processing"}}),
            FakeResponse(
                payload={
                    "data": {
                        "status": "completed",
                        "outputs": ["https://cdn.example.com/result.png"],
                    }
                }
            ),
            FakeResponse(
                body=_png(),
                headers={"content-type": "image/png", "content-length": str(len(_png()))},
            ),
        ]
    )

    def fake_request(session, method, url, **kwargs):
        del session
        calls.append((method, url, kwargs))
        return next(responses)

    monkeypatch.setattr(generate_image, "guarded_request", fake_request)
    monkeypatch.setattr(generate_image.time, "sleep", lambda _: None)

    result = generate_image.generate_atlas(
        "ephemeral prompt", 1024, 1024, "ephemeral-key", "qwen-image-3.0/text-to-image"
    )

    assert result == _png()
    assert [method for method, _, _ in calls] == ["POST", "GET", "GET", "GET"]
    assert calls[0][2]["json"] == {
        "model": "qwen-image-3.0/text-to-image",
        "prompt": "ephemeral prompt",
        "size": "1024*1024",
        "n": 1,
    }
    assert calls[-1][1] == "https://cdn.example.com/result.png"
    assert "headers" not in calls[-1][2]


def test_atlas_submission_failure_is_not_retried(monkeypatch):
    calls = []

    def fake_request(session, method, url, **kwargs):
        del session, url, kwargs
        calls.append(method)
        return FakeResponse(status_code=503)

    monkeypatch.setattr(generate_image, "guarded_request", fake_request)

    with pytest.raises(RuntimeError, match="submission failed with HTTP 503"):
        generate_image.generate_atlas("prompt", 1024, 1024, "key", "model")
    assert calls == ["POST"]


def test_atlas_application_error_is_rejected_and_response_is_closed():
    response = FakeResponse(payload={"code": 429, "data": {"id": "unexpected"}})

    with pytest.raises(RuntimeError, match="API code 429"):
        generate_image._atlas_json_response(response, "submission")
    assert response.closed is True


def test_atlas_rejects_non_https_output_before_download(monkeypatch):
    responses = iter(
        [
            FakeResponse(payload={"id": "prediction-1"}),
            FakeResponse(
                payload={
                    "status": "completed",
                    "outputs": ["http://cdn.example.com/result.png"],
                }
            ),
        ]
    )
    calls = []

    def fake_request(session, method, url, **kwargs):
        del session, kwargs
        calls.append((method, url))
        return next(responses)

    monkeypatch.setattr(generate_image, "guarded_request", fake_request)

    with pytest.raises(RuntimeError, match="non-HTTPS"):
        generate_image.generate_atlas("prompt", 1024, 1024, "key", "model")
    assert len(calls) == 2


def test_atlas_polling_is_bounded(monkeypatch):
    responses = iter(
        [
            FakeResponse(payload={"id": "prediction-1"}),
            FakeResponse(payload={"status": "processing"}),
            FakeResponse(payload={"status": "processing"}),
        ]
    )
    calls = []

    def fake_request(session, method, url, **kwargs):
        del session, url, kwargs
        calls.append(method)
        return next(responses)

    monkeypatch.setattr(generate_image, "guarded_request", fake_request)
    monkeypatch.setattr(generate_image.time, "sleep", lambda _: None)
    monkeypatch.setattr(generate_image, "ATLAS_MAX_POLL_ATTEMPTS", 2)

    with pytest.raises(TimeoutError, match="polling limit"):
        generate_image.generate_atlas("prompt", 1024, 1024, "key", "model")
    assert calls == ["POST", "GET", "GET"]


def test_atlas_download_enforces_declared_size_limit(monkeypatch):
    response = FakeResponse(
        body=_png(),
        headers={
            "content-type": "image/png",
            "content-length": str(generate_image.ATLAS_MAX_IMAGE_BYTES + 1),
        },
    )
    monkeypatch.setattr(
        generate_image,
        "guarded_request",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(RuntimeError, match="25 MiB"):
        generate_image._atlas_download_image("https://cdn.example.com/result.png")
    assert response.closed is True


def test_atlas_credential_mapping_and_reference_input_contract(monkeypatch):
    monkeypatch.setenv("ATLASCLOUD_API_KEY", "ephemeral-key")
    assert generate_image._get_api_key("atlas") == "ephemeral-key"
    monkeypatch.setattr(
        generate_image,
        "generate_atlas",
        lambda *args, **kwargs: pytest.fail("provider dispatch must not occur"),
    )

    with pytest.raises(ValueError, match="does not declare reference-image support"):
        generate_image.generate_image(
            "prompt",
            "1:1",
            "atlas",
            "qwen-image-3.0/text-to-image",
            "ephemeral-key",
            "reference.png",
        )
