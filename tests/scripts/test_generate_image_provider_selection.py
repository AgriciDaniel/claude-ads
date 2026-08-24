"""Provider-neutral selection contract for the local image CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import generate_image  # noqa: E402


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
        return b"image"

    monkeypatch.setattr(generate_image, "generate_gemini", fake_generate)
    image, _, _ = generate_image.generate_image(
        "ephemeral prompt",
        "1:1",
        "gemini",
        "operator-approved-model",
        "ephemeral-key",
        str(reference),
    )

    assert image == b"image"
    assert calls == [("operator-approved-model", str(reference))]


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


def test_muapi_uses_current_catalog_schema_and_bounded_polling(monkeypatch):
    responses = iter([
        {
            "models": [
                {"name": "flux-dev", "category": "Text to Image", "endpoint": "/api/v1/flux-dev"},
            ],
        },
        {
            "input_schema": {
                "schemas": {
                    "input_data": {
                        "properties": {
                            "prompt": {"type": "string"},
                            "width": {"minValue": 128, "maxValue": 2048, "step": 64},
                            "height": {"minValue": 128, "maxValue": 2048, "step": 64},
                            "num_images": {"minValue": 1, "maxValue": 4, "step": 1},
                        },
                    },
                },
            },
        },
        {"request_id": "request-1", "status": "queued"},
        {"status": "processing"},
        {"status": "completed", "outputs": ["https://cdn.example.test/image.png"]},
    ])
    calls = []

    def fake_request(method, path, api_key, body=None):
        calls.append((method, path, body, api_key))
        return next(responses)

    monkeypatch.setattr(generate_image, "_muapi_request", fake_request)
    monkeypatch.setattr(generate_image, "_muapi_download", lambda url: b"image")
    monkeypatch.setattr(generate_image.time, "sleep", lambda _: None)

    image = generate_image.generate_muapi(
        "a blue square", 1080, 1080, "ephemeral-key", "flux-dev"
    )

    assert image == b"image"
    assert calls[2][0:3] == ("POST", "/api/v1/flux-dev", {
        "prompt": "a blue square",
        "width": 1088,
        "height": 1088,
        "num_images": 1,
    })
    assert [call[0] for call in calls[3:]] == ["GET", "GET"]


def test_muapi_does_not_accept_a_local_reference_snapshot(monkeypatch):
    monkeypatch.setattr(
        generate_image,
        "_muapi_find_model",
        lambda *args: pytest.fail("catalog lookup must not occur for unsupported reference input"),
    )
    with pytest.raises(ValueError, match="does not declare reference-image support"):
        generate_image.generate_muapi(
            "prompt", 1024, 1024, "ephemeral-key", "flux-dev", "reference.png"
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
