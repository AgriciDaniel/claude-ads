"""Provider-neutral selection contract for the local image CLI."""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import generate_image  # noqa: E402


_VALID_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def _lifecycle() -> dict:
    return {
        "schema_version": "1.0.0",
        "lifecycle_id": "provider-selection-test",
        "classification": "internal",
        "retention": {
            "minimum_seconds": 0,
            "mode": "operator-defined",
            "delete_after": "2026-07-12T16:00:00Z",
            "purpose": "Verify explicit provider and model selection",
            "exception_reason": None,
        },
        "encryption": {
            "at_rest": "verified",
            "in_transit": "verified",
            "evidence_refs": ["operator-attestation:test-encryption"],
        },
        "access": {
            "owner": "test-owner",
            "authorized_roles": ["test-runner"],
            "access_log_locator": None,
        },
        "deletion": {
            "status": "scheduled",
            "method": "Test cleanup",
            "verification_required": True,
            "verification_artifact_locator": None,
        },
        "incident": {
            "owner": "test-owner",
            "reporting_channel": "Private test channel",
            "status": "not-triggered",
            "record_locator": None,
        },
    }


@pytest.mark.parametrize(
    ("provider", "model", "message"),
    [
        (None, "operator-model", "Image provider is required"),
        ("gemini", None, "Image model is required"),
        ("  ", "operator-model", "Image provider is required"),
        ("gemini", "  ", "Image model is required"),
    ],
)
def test_selection_requires_both_provider_and_model(provider, model, message):
    with pytest.raises(ValueError, match=message):
        generate_image._require_selection(provider, model)


def test_gemini_dispatch_uses_exact_model_without_upgrade_or_fallback(monkeypatch, tmp_path):
    reference = tmp_path / "reference.png"
    reference.write_bytes(b"reference")
    calls = []

    def fake_generate(prompt, width, height, api_key, model, reference_path):
        calls.append((model, reference_path))
        return _VALID_PNG

    monkeypatch.setattr(generate_image, "generate_gemini", fake_generate)
    image, _, _ = generate_image.generate_image(
        "ephemeral prompt",
        "1:1",
        "gemini",
        "operator-approved-model",
        "ephemeral-key",
        str(reference),
    )

    assert image == _VALID_PNG
    assert calls == [("operator-approved-model", str(reference))]


def test_provider_output_must_be_a_complete_supported_png(monkeypatch):
    monkeypatch.setattr(generate_image, "generate_openai", lambda *args: b"not-an-image")

    with pytest.raises(RuntimeError, match="not a valid supported PNG"):
        generate_image.generate_image(
            "ephemeral prompt",
            "1:1",
            "openai",
            "operator-approved-model",
            "ephemeral-key",
        )


def test_provider_output_size_limit_is_enforced_after_in_memory_adapters(monkeypatch):
    monkeypatch.setattr(generate_image, "MAX_GENERATED_IMAGE_BYTES", 8)
    monkeypatch.setattr(generate_image, "generate_openai", lambda *args: _VALID_PNG)

    with pytest.raises(RuntimeError, match="25 MiB limit"):
        generate_image.generate_image(
            "ephemeral prompt",
            "1:1",
            "openai",
            "operator-approved-model",
            "ephemeral-key",
        )


def test_streamed_provider_response_is_bounded_typed_and_closed(monkeypatch):
    class Response:
        status_code = 200
        headers = {
            "content-type": "image/png; charset=binary",
            "content-length": str(len(_VALID_PNG)),
        }

        def __init__(self):
            self.closed = False

        def iter_content(self, chunk_size):
            assert chunk_size == 64 * 1024
            yield _VALID_PNG[:20]
            yield _VALID_PNG[20:]

        def close(self):
            self.closed = True

    response = Response()
    assert generate_image._bounded_png_response(response, "provider") == _VALID_PNG
    assert response.closed is True

    response = Response()
    response.headers = {"content-type": "text/html"}
    with pytest.raises(RuntimeError, match="unsupported content type"):
        generate_image._bounded_png_response(response, "provider")
    assert response.closed is True

    response = Response()
    response.headers = {"content-type": "image/png"}
    monkeypatch.setattr(generate_image, "MAX_GENERATED_IMAGE_BYTES", 8)
    with pytest.raises(RuntimeError, match="25 MiB limit"):
        generate_image._bounded_png_response(response, "provider")
    assert response.closed is True


@pytest.mark.parametrize("path", ["asset.jpg", "asset.jpeg", "asset", "asset.png.exe"])
def test_generated_output_path_must_match_png_contract(path):
    with pytest.raises(ValueError, match="must use the .png extension"):
        generate_image._require_png_output_path(path)


def test_reference_image_is_not_silently_dropped_for_unsupported_adapter(monkeypatch):
    monkeypatch.setattr(
        generate_image,
        "generate_openai",
        lambda *args, **kwargs: pytest.fail("provider dispatch must not occur"),
    )
    with pytest.raises(ValueError, match="does not declare reference-image support"):
        generate_image.generate_image(
            "ephemeral prompt",
            "1:1",
            "openai",
            "operator-approved-model",
            "ephemeral-key",
            "reference.png",
        )


def test_cli_requires_selection_before_credentials_or_network(monkeypatch, capsys):
    monkeypatch.delenv("ADS_IMAGE_PROVIDER", raising=False)
    monkeypatch.delenv("ADS_IMAGE_MODEL", raising=False)
    monkeypatch.setattr(
        generate_image,
        "_get_api_key",
        lambda provider: pytest.fail("credential lookup must not occur"),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_image.py",
            "ephemeral prompt",
            "--model",
            "operator-model",
            "--data-lifecycle",
            "unused.json",
        ],
    )

    with pytest.raises(SystemExit) as exc:
        generate_image.main()

    assert exc.value.code == 2
    assert "image provider is required" in capsys.readouterr().err.lower()


def test_environment_selection_is_recorded_exactly(monkeypatch, tmp_path, capsys):
    lifecycle_path = tmp_path / "lifecycle.json"
    lifecycle_path.write_text(json.dumps(_lifecycle()), encoding="utf-8")
    monkeypatch.setenv("ADS_IMAGE_PROVIDER", "gemini")
    monkeypatch.setenv("ADS_IMAGE_MODEL", "operator-approved-model")
    monkeypatch.setenv("CLAUDE_ADS_OUTPUT_ROOT", str(tmp_path))
    monkeypatch.setattr(generate_image, "_get_api_key", lambda provider: "ephemeral-key")
    monkeypatch.setattr(
        generate_image,
        "generate_image",
        lambda *args, **kwargs: (b"private-image", 100, 100),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_image.py",
            "private prompt",
            "--output",
            "asset.png",
            "--json",
            "--data-lifecycle",
            str(lifecycle_path),
        ],
    )

    generate_image.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["provider"] == "gemini"
    assert payload["model"] == "operator-approved-model"
    assert payload["file_locator"] == "asset.png"
    assert "private prompt" not in json.dumps(payload)


def test_script_and_reference_forbid_implicit_provider_model_selection(repo_root):
    script = (repo_root / "scripts/generate_image.py").read_text(encoding="utf-8")
    reference = (repo_root / "ads/references/image-providers.md").read_text(
        encoding="utf-8"
    )
    normalized_reference = " ".join(reference.split())
    for forbidden in (
        "DEFAULT_PROVIDER",
        "DEFAULT_MODEL_",
        "Auto-upgrade",
        "Falling back to",
        "banana-claude",
        "Preferred method",
    ):
        assert forbidden not in script
    assert "does not promise a default image provider, model" in normalized_reference
    assert "must not select, upgrade, or substitute" in normalized_reference
