"""Regression gates for bounded creative workers and qualitative plan assets."""

from __future__ import annotations

import json
import re


CREATIVE_AGENTS = {
    "creative-strategist.md",
    "copy-writer.md",
    "visual-designer.md",
    "format-adapter.md",
}

PLAN_ASSETS = {
    "agency.md",
    "b2b-enterprise.md",
    "ecommerce-creative.md",
    "ecommerce.md",
    "finance.md",
    "generic.md",
    "healthcare.md",
    "info-products.md",
    "local-service.md",
    "mobile-app.md",
    "real-estate.md",
    "saas.md",
}

SOURCE_MAP = {
    "Google": "google-rsa-official",
    "Meta": "meta-video-ads-official",
    "YouTube": "youtube-google-ads-video-official",
    "LinkedIn": "linkedin-ads-guide-official",
    "TikTok": "tiktok-ad-format-policy-official",
    "Microsoft": "microsoft-ad-types-official",
    "Apple": "apple-ads-creative-official",
    "Amazon": "amazon-creative-acceptance-official",
    "Reddit": "reddit-ads-help-official",
    "Pinterest": "pinterest-ad-specs-official",
    "Snapchat": "snap-creative-specs-official",
    "X": "x-creative-specs-official",
}

LEGACY_AGENT_PATTERNS = {
    "home-relative install path": re.compile(r"~/(?:\.claude|\.banana)"),
    "absolute private path": re.compile(r"(?:/Users/|(?:/var)?/home/|[A-Z]:\\Users\\)"),
    "ambient CWD input": re.compile(r"current (?:working )?directory", re.IGNORECASE),
    "shared ad-assets output": re.compile(r"(?:^|[ `])\.?/ad-assets/", re.MULTILINE),
    "legacy final brief": re.compile(r"campaign-brief\.md"),
    "legacy final generation manifest": re.compile(r"generation-manifest\.json"),
    "legacy final format report": re.compile(r"format-report\.md"),
    "assumed provider": re.compile(
        r"\b(?:banana|gemini|openai|stability|replicate)\b", re.IGNORECASE
    ),
    "pinned model": re.compile(r"^model\s*:", re.MULTILINE),
    "pinned turn limit": re.compile(r"^maxTurns\s*:", re.MULTILINE),
}

FORBIDDEN_PLAN_PHRASES = (
    "recommended platform mix",
    "budget guidelines",
    "budget allocation",
    "bidding strategy selection",
    "kpi targets",
    "kill rule",
    "when to scale",
    "minimum viable",
    "min monthly budget",
    "outperform",
    "lower cpa",
    "higher roas",
    "primary platform",
)


def test_exact_legacy_surface_inventory_is_covered(repo_root):
    agents = {path.name for path in (repo_root / "agents").glob("*.md")}
    assets = {
        path.name for path in (repo_root / "skills/ads-plan/assets").glob("*.md")
    }
    assert CREATIVE_AGENTS <= agents
    assert assets == PLAN_ASSETS


def test_creative_agents_are_bounded_provider_neutral_workers(repo_root):
    for filename in CREATIVE_AGENTS:
        text = (repo_root / "agents" / filename).read_text(encoding="utf-8")
        lowered = text.lower()
        for label, pattern in LEGACY_AGENT_PATTERNS.items():
            assert not pattern.search(text), f"{filename} retains {label}"
        for required in (
            "plugin_root",
            "run_id",
            "task_id",
            "creative-source-registry.md",
            "creative-worker-result.schema.json",
            "untrusted data",
            "conductor",
            "canonical",
        ):
            assert required in lowered, f"{filename} omits {required!r}"
        assert re.search(r"current\s+official\s+source\s+ids?", lowered)
        assert re.search(r"(?:do not|never)[^.\n]{0,100}\bwrite\b", lowered)
        assert "runtime, model, provider, mcp server" in lowered


def test_visual_candidates_are_run_scoped_and_conductor_owned(repo_root):
    visual = (repo_root / "agents/visual-designer.md").read_text(encoding="utf-8")
    adapter = (repo_root / "agents/format-adapter.md").read_text(encoding="utf-8")
    run_path = ".claude-ads/runs/<run_id>/workers/<task_id>/"
    for text in (visual, adapter):
        assert run_path in text
        assert "candidate_artifacts" in text
        assert "shared" in text.lower()
    assert "Do not select winners" in visual
    assert "Never regenerate, transform, publish, upload, or mutate" in adapter


def test_creative_source_registry_is_complete_and_registered(repo_root):
    path = repo_root / "ads/references/creative-source-registry.md"
    text = path.read_text(encoding="utf-8")
    source_doc = json.loads(
        (repo_root / "control-plane/manifests/source-ledger.json").read_text(
            encoding="utf-8"
        )
    )
    registered = {source["id"] for source in source_doc["sources"]}
    rows = dict(
        re.findall(r"^\| ([^|]+?) \| `([^`]+)` \|", text, flags=re.MULTILINE)
    )
    assert rows == SOURCE_MAP
    assert set(rows.values()) <= registered
    assert "untrusted data" in text
    assert "return `needs_input`" in text.lower()
    assert "do not infer one platform's limits" in text.lower()


def test_creative_worker_schema_enforces_run_scoped_candidates(repo_root):
    schema = json.loads(
        (
            repo_root
            / "control-plane/schemas/creative-worker-result.schema.json"
        ).read_text(encoding="utf-8")
    )
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    assert schema["properties"]["worker"]["enum"] == [
        "creative-strategist",
        "copy-writer",
        "visual-designer",
        "format-adapter",
    ]
    artifact = schema["properties"]["candidate_artifacts"]["items"]
    assert artifact["additionalProperties"] is False
    pattern = re.compile(artifact["properties"]["candidate_path"]["pattern"])
    assert pattern.fullmatch(
        ".claude-ads/runs/run-alpha/workers/visual-task/candidates/asset.png"
    )
    for unsafe in (
        "asset.png",
        "./ad-assets/asset.png",
        ".claude-ads/runs/run-alpha/report.pdf",
        ".claude-ads/runs/run-alpha/workers/../report.pdf",
        ".claude-ads/runs/run-alpha/workers/visual-task/../report.pdf",
        ".claude-ads/runs/../workers/visual-task/report.pdf",
    ):
        assert not pattern.fullmatch(unsafe)


def test_every_plan_asset_is_qualitative_unscored_and_gated(repo_root):
    asset_root = repo_root / "skills/ads-plan/assets"
    for filename in PLAN_ASSETS:
        text = (asset_root / filename).read_text(encoding="utf-8")
        lowered = text.lower()
        assert "> status: qualitative, unscored planning aid" in lowered
        for heading in (
            "## Required gates",
            "## Planning questions",
            "## Candidate considerations",
            "## Output guardrails",
        ):
            assert heading in text, f"{filename} omits {heading}"
        assert "context gate" in lowered
        assert "regulatory gate" in lowered
        assert re.search(r"current\s+official\s+source\s+ids?", lowered)
        assert "do not" in lowered
        for phrase in FORBIDDEN_PLAN_PHRASES:
            assert phrase not in lowered, f"{filename} retains {phrase!r}"


def test_plan_assets_have_no_frozen_numbers_or_threshold_notation(repo_root):
    for path in (repo_root / "skills/ads-plan/assets").glob("*.md"):
        text = path.read_text(encoding="utf-8")
        normalized = text.replace("B2B", "business-to-business")
        assert not re.search(r"\d", normalized), f"{path.name} retains a frozen number"
        assert "$" not in text and "%" not in text
        assert not re.search(r"(?:>=|<=|[≥≤]|\b\d+(?:\.\d+)?[xX]\b)", text)
        assert not re.search(
            r"\b(?:pause|kill|scale|increase|decrease)\b.{0,80}"
            r"\b(?:after|above|below|target|when|if)\b",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )


def test_copy_frameworks_are_unscored_and_live_spec_routed(repo_root):
    text = (repo_root / "ads/references/copy-frameworks.md").read_text(
        encoding="utf-8"
    )
    lowered = text.lower()
    for framework in (
        "Attention–Interest–Desire–Action",
        "Problem–Agitation–Solution",
        "Before–After–Bridge",
        "Promise–Picture–Proof–Push",
        "Feature–Advantage–Benefit",
        "Star–Story–Solution",
    ):
        assert framework in text
    assert "qualitative, unscored practitioner patterns" in lowered
    assert "creative-source-registry.md" in text
    assert "current official source id" in lowered
    assert "return `needs_input`" in lowered
    normalized = text.replace("4P", "promise-pattern")
    assert not re.search(r"\d", normalized)
    assert not re.search(
        r"\b\d+(?:\.\d+)?\s*(?:chars?|characters?|seconds?|minutes?|hours?|days?|%)",
        text,
        flags=re.IGNORECASE,
    )
    for phrase in (
        "platform fit",
        "best for",
        "when in doubt",
        "default to",
        "meta primary text",
        "google rsa headline",
    ):
        assert phrase not in lowered
