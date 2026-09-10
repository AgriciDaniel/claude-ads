"""Deterministic, privacy-aware renderers for validated report bundles.

JSON remains the canonical artifact.  This module produces human-readable
views without recalculating scores, loading remote assets, or embedding the
source bundle in the output.
"""

from __future__ import annotations

import html
import importlib
import json
import os
import re
import stat
import tempfile
from pathlib import Path
from typing import Any, Mapping

from .contracts import ContractError, validate_contract


class ReportRenderError(ValueError):
    """Raised when a report cannot be rendered or written safely."""


class PDFDependencyError(ReportRenderError):
    """Raised when the optional PDF renderer is unavailable."""


_EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])")
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(access[_-]?token|refresh[_-]?token|api[_-]?key|client[_-]?secret|"
    r"password|passwd|authorization|cookie)\s*([:=])\s*([^\s&;,]+)"
)
_SENSITIVE_KEY_RE = re.compile(
    r"(?i)(^|[_-])(access[_-]?token|refresh[_-]?token|api[_-]?key|client[_-]?secret|"
    r"password|passwd|authorization|cookie|set[_-]?cookie|email|phone)([_-]|$)"
)
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_STATUS_LABELS = {
    "normal": "Normal",
    "provisional": "Provisional",
    "insufficient_evidence": "Insufficient evidence",
}
_COMPLETENESS_LABELS = {"complete": "Complete", "partial": "Partial", "failed": "Failed"}


def _redact_text(value: str) -> str:
    value = _CONTROL_CHARS_RE.sub("", value).replace("\r\n", "\n").replace("\r", "\n")
    value = _BEARER_RE.sub("Bearer [REDACTED]", value)
    value = _SECRET_ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", value)
    return _EMAIL_RE.sub("[REDACTED EMAIL]", value)


def _redact_value(value: Any, *, key: str | None = None) -> Any:
    if key is not None and _SENSITIVE_KEY_RE.search(key):
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {str(item_key): _redact_value(item, key=str(item_key)) for item_key, item in value.items()}
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_value(item) for item in value]
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _text(value: Any) -> str:
    if value is None:
        return ""
    return _redact_text(str(value)).replace("\n", " ").strip()


def _md(value: Any) -> str:
    """Make untrusted text inert in a single Markdown paragraph."""

    text = _text(value)
    return re.sub(r"([\\`*_{}\[\]()<>#+.!|>-])", r"\\\1", text)


def _html(value: Any) -> str:
    return html.escape(_text(value), quote=True)


def _canonical_json(value: Any) -> str:
    return json.dumps(_redact_value(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _validated_bundle(bundle: Mapping[str, Any]) -> Mapping[str, Any]:
    try:
        validate_contract("report-bundle", bundle)
    except ContractError as exc:
        raise ReportRenderError(f"invalid report bundle: {exc}") from exc
    for field in ("contradictions", "actions"):
        if field in bundle and not isinstance(bundle[field], list):
            raise ReportRenderError(f"$.{field} must be an array when present")
    return bundle


def _score_text(score: Any) -> str:
    if score is None:
        return "Not scored"
    return f"{float(score):.2f} / 100"


def _coverage_text(coverage: Any) -> str:
    return f"{float(coverage):.2f}%"


def _controls(bundle: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(control["control_id"]): control for control in bundle["control_definitions"]}


def _findings(bundle: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return sorted(bundle["findings"], key=lambda finding: str(finding["control_id"]))


def _categories(bundle: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return sorted(bundle["scoring"]["categories"], key=lambda category: str(category.get("category", "")))


def _extension_item_text(item: Any) -> str:
    if isinstance(item, str):
        return _text(item)
    if isinstance(item, Mapping):
        preferred = ("summary", "title", "action", "claim", "description", "recommendation")
        headline = next((_text(item[key]) for key in preferred if item.get(key)), "")
        details = [
            f"{str(key).replace('_', ' ').title()}: {_text(value)}"
            for key, value in sorted(item.items(), key=lambda pair: str(pair[0]))
            if key not in preferred and value not in (None, "", [], {})
        ]
        if headline and details:
            return f"{headline} ({'; '.join(details)})"
        return headline or "; ".join(details) or _canonical_json(item)
    return _text(item)


def _actions(bundle: Mapping[str, Any]) -> list[Any]:
    explicit = list(bundle.get("actions", []))
    if explicit:
        return explicit
    return [
        {
            "action": finding["recommendation"],
            "confidence": finding["confidence"],
            "control_id": finding["control_id"],
        }
        for finding in _findings(bundle)
        if finding["status"] in {"fail", "unknown"} and _text(finding.get("recommendation"))
    ]


def render_markdown(bundle: Mapping[str, Any]) -> str:
    """Render a validated ReportBundle as deterministic Markdown."""

    bundle = _validated_bundle(bundle)
    manifest = bundle["run_manifest"]
    snapshot = bundle["account_snapshot"]
    scoring = bundle["scoring"]
    controls = _controls(bundle)
    completeness = str(manifest["completeness"])
    score_status = str(scoring["status"])
    account = snapshot["account"]

    lines = [
        "# Claude Ads Audit Report",
        "",
        f"> Run completeness: **{_COMPLETENESS_LABELS[completeness]}** · Evidence status: **{_STATUS_LABELS[score_status]}**",
        "",
        "## Run summary",
        "",
        f"- Run ID: {_md(manifest['run_id'])}",
        f"- Started: {_md(manifest['started_at'])}",
        f"- Platform: {_md(str(account['platform']).title())}",
        f"- Account: {_md(account.get('name') or account['account_id'])}",
        f"- Window: {_md(snapshot['window']['start'])} to {_md(snapshot['window']['end'])}",
        f"- Privacy class: {_md(str(manifest['privacy_class']).title())}",
        "",
        "## Decision status",
        "",
        f"- Run completeness: **{_COMPLETENESS_LABELS[completeness]}**",
        f"- Evidence status: **{_STATUS_LABELS[score_status]}**",
        f"- Health score: **{_score_text(scoring['health_score'])}**",
        f"- Evidence coverage: **{_coverage_text(scoring['evidence_coverage'])}**",
    ]
    if completeness != "complete":
        lines.extend(("", "> WARNING: Required work did not complete; this report must not be presented as a complete audit."))
    if score_status == "provisional":
        lines.extend(("", "> WARNING: The health score is provisional because evidence coverage is below the normal threshold."))
    elif score_status == "insufficient_evidence":
        lines.extend(("", "> WARNING: Evidence is insufficient for a defensible health score."))

    lines.extend(("", "## Category health", ""))
    categories = _categories(bundle)
    if categories:
        for category in categories:
            lines.append(
                f"- **{_md(str(category.get('category', 'Uncategorized')).title())}:** "
                f"{_score_text(category.get('health_score'))}; evidence {_coverage_text(category.get('evidence_coverage', 0))}"
            )
    else:
        lines.append("No category scores were supplied.")

    lines.extend(("", "## Findings", ""))
    findings = _findings(bundle)
    if not findings:
        lines.append("No findings were supplied.")
    for finding in findings:
        control = controls.get(str(finding["control_id"]), {})
        heading = (
            f"### [{_md(str(finding['status']).replace('_', ' ').upper())}] "
            f"{_md(finding['control_id'])} — {_md(str(control.get('category', 'uncategorized')).title())}"
        )
        lines.extend(
            (
                heading,
                "",
                f"- Severity: {_md(str(control.get('severity', 'not specified')).title())}",
                f"- Confidence: {_md(str(finding['confidence']).title())}",
                f"- Source classification: {_md(str(finding.get('source_classification', 'not specified')).replace('_', ' ').title())}",
                "",
                f"**Observation:** {_md(finding['observation']) or 'Not supplied.'}",
                "",
                f"**Diagnosis:** {_md(finding['diagnosis']) or 'Not supplied.'}",
                "",
                f"**Recommended action:** {_md(finding['recommendation']) or 'No action supplied.'}",
                "",
                "**Evidence:**",
                "",
            )
        )
        if finding["evidence"]:
            for index, evidence in enumerate(finding["evidence"], start=1):
                lines.extend((f"{index}.", "", f"        {_canonical_json(evidence)}", ""))
        else:
            lines.extend(("No evidence was supplied.", ""))

    lines.extend(("## Contradictions", ""))
    contradictions = list(bundle.get("contradictions", []))
    if contradictions:
        lines.extend(f"- {_md(_extension_item_text(item))}" for item in contradictions)
    else:
        lines.append("No contradictions were reported.")

    lines.extend(("", "## Prioritized actions", ""))
    actions = _actions(bundle)
    if actions:
        lines.extend(f"{index}. {_md(_extension_item_text(item))}" for index, item in enumerate(actions, start=1))
    else:
        lines.append("No follow-up actions were reported.")

    lines.extend(("", "---", "", "Generated deterministically from ReportBundle JSON. Scores were not recalculated.", ""))
    return "\n".join(lines)


_HTML_STYLE = """
:root{color-scheme:light;--ink:#172033;--muted:#596579;--line:#d8dee9;--paper:#fff;--soft:#f5f7fa;--ok:#18794e;--warn:#9a6700;--bad:#c62828}
*{box-sizing:border-box}body{margin:0;background:#eef1f5;color:var(--ink);font:15px/1.55 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:960px;margin:32px auto;padding:40px;background:var(--paper);box-shadow:0 8px 30px #17203318}h1,h2,h3{line-height:1.2}h1{margin-top:0}h2{margin-top:2rem;border-bottom:1px solid var(--line);padding-bottom:.4rem}h3{margin-top:1.5rem}.banner{padding:12px 16px;border-left:5px solid var(--ok);background:var(--soft);font-weight:700}.banner.partial,.banner.failed,.banner.provisional{border-color:var(--warn)}.banner.insufficient_evidence{border-color:var(--bad)}.warning{padding:10px 14px;background:#fff6d6;border:1px solid #e9c46a}.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.metric{padding:14px;background:var(--soft);border:1px solid var(--line)}.metric strong{display:block;font-size:1.25rem}.meta{display:grid;grid-template-columns:max-content 1fr;gap:4px 16px}.finding{padding:18px;margin:14px 0;border:1px solid var(--line);border-radius:6px}.status-pass{border-left:5px solid var(--ok)}.status-fail{border-left:5px solid var(--bad)}.status-unknown{border-left:5px solid var(--warn)}pre{overflow-wrap:anywhere;white-space:pre-wrap;background:var(--soft);padding:10px;border:1px solid var(--line)}dt{font-weight:700}dd{margin:0 0 10px}footer{margin-top:2rem;padding-top:1rem;border-top:1px solid var(--line);color:var(--muted)}@media print{body{background:#fff}main{box-shadow:none;margin:0;max-width:none}}
""".strip()


def render_html(bundle: Mapping[str, Any]) -> str:
    """Render a validated ReportBundle as self-contained deterministic HTML."""

    bundle = _validated_bundle(bundle)
    manifest = bundle["run_manifest"]
    snapshot = bundle["account_snapshot"]
    scoring = bundle["scoring"]
    controls = _controls(bundle)
    completeness = str(manifest["completeness"])
    score_status = str(scoring["status"])
    account = snapshot["account"]
    warnings: list[str] = []
    if completeness != "complete":
        warnings.append("Required work did not complete; this report must not be presented as a complete audit.")
    if score_status == "provisional":
        warnings.append("The health score is provisional because evidence coverage is below the normal threshold.")
    elif score_status == "insufficient_evidence":
        warnings.append("Evidence is insufficient for a defensible health score.")

    category_html = "".join(
        "<li><strong>{}</strong>: {}; evidence {}</li>".format(
            _html(str(category.get("category", "Uncategorized")).title()),
            _html(_score_text(category.get("health_score"))),
            _html(_coverage_text(category.get("evidence_coverage", 0))),
        )
        for category in _categories(bundle)
    ) or "<li>No category scores were supplied.</li>"

    finding_parts: list[str] = []
    for finding in _findings(bundle):
        control = controls.get(str(finding["control_id"]), {})
        evidence = "".join(f"<pre>{html.escape(_canonical_json(item))}</pre>" for item in finding["evidence"])
        if not evidence:
            evidence = "<p>No evidence was supplied.</p>"
        status = str(finding["status"])
        finding_parts.append(
            f'<article class="finding status-{html.escape(status)}">'
            f"<h3>[{_html(status.replace('_', ' ').upper())}] {_html(finding['control_id'])} — "
            f"{_html(str(control.get('category', 'uncategorized')).title())}</h3>"
            "<dl>"
            f"<dt>Severity</dt><dd>{_html(str(control.get('severity', 'not specified')).title())}</dd>"
            f"<dt>Confidence</dt><dd>{_html(str(finding['confidence']).title())}</dd>"
            f"<dt>Source classification</dt><dd>{_html(str(finding.get('source_classification', 'not specified')).replace('_', ' ').title())}</dd>"
            f"<dt>Observation</dt><dd>{_html(finding['observation']) or 'Not supplied.'}</dd>"
            f"<dt>Diagnosis</dt><dd>{_html(finding['diagnosis']) or 'Not supplied.'}</dd>"
            f"<dt>Recommended action</dt><dd>{_html(finding['recommendation']) or 'No action supplied.'}</dd>"
            f"</dl><h4>Evidence</h4>{evidence}</article>"
        )
    findings_html = "".join(finding_parts) or "<p>No findings were supplied.</p>"

    contradictions = list(bundle.get("contradictions", []))
    contradictions_html = (
        "<ul>" + "".join(f"<li>{_html(_extension_item_text(item))}</li>" for item in contradictions) + "</ul>"
        if contradictions
        else "<p>No contradictions were reported.</p>"
    )
    actions = _actions(bundle)
    actions_html = (
        "<ol>" + "".join(f"<li>{_html(_extension_item_text(item))}</li>" for item in actions) + "</ol>"
        if actions
        else "<p>No follow-up actions were reported.</p>"
    )
    warnings_html = "".join(f'<p class="warning"><strong>Warning:</strong> {_html(item)}</p>' for item in warnings)

    return (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>Claude Ads Audit Report</title><style>" + _HTML_STYLE + "</style></head><body><main>"
        "<h1>Claude Ads Audit Report</h1>"
        f'<p class="banner {html.escape(completeness)} {html.escape(score_status)}">Run completeness: '
        f"{_html(_COMPLETENESS_LABELS[completeness])} · Evidence status: {_html(_STATUS_LABELS[score_status])}</p>"
        "<h2>Run summary</h2><dl class=\"meta\">"
        f"<dt>Run ID</dt><dd>{_html(manifest['run_id'])}</dd><dt>Started</dt><dd>{_html(manifest['started_at'])}</dd>"
        f"<dt>Platform</dt><dd>{_html(str(account['platform']).title())}</dd>"
        f"<dt>Account</dt><dd>{_html(account.get('name') or account['account_id'])}</dd>"
        f"<dt>Window</dt><dd>{_html(snapshot['window']['start'])} to {_html(snapshot['window']['end'])}</dd>"
        f"<dt>Privacy class</dt><dd>{_html(str(manifest['privacy_class']).title())}</dd></dl>"
        "<h2>Decision status</h2><div class=\"metrics\">"
        f'<div class="metric">Run completeness<strong>{_html(_COMPLETENESS_LABELS[completeness])}</strong></div>'
        f'<div class="metric">Evidence status<strong>{_html(_STATUS_LABELS[score_status])}</strong></div>'
        f'<div class="metric">Health score<strong>{_html(_score_text(scoring["health_score"]))}</strong></div>'
        f'<div class="metric">Evidence coverage<strong>{_html(_coverage_text(scoring["evidence_coverage"]))}</strong></div></div>'
        + warnings_html
        + f"<h2>Category health</h2><ul>{category_html}</ul><h2>Findings</h2>{findings_html}"
        + f"<h2>Contradictions</h2>{contradictions_html}<h2>Prioritized actions</h2>{actions_html}"
        + "<footer>Generated deterministically from ReportBundle JSON. Scores were not recalculated.</footer>"
        + "</main></body></html>\n"
    )


def render_pdf(bundle: Mapping[str, Any]) -> bytes:
    """Render PDF bytes through the optional WeasyPrint bridge."""

    source = render_html(bundle)
    try:
        weasyprint = importlib.import_module("weasyprint")
    except (ImportError, OSError) as exc:
        raise PDFDependencyError(
            "PDF rendering requires the optional 'weasyprint' package and its system libraries; "
            "install WeasyPrint or render Markdown/HTML instead"
        ) from exc
    try:
        result = weasyprint.HTML(string=source, base_url=None).write_pdf()
    except Exception as exc:
        raise ReportRenderError(f"PDF rendering failed: {exc}") from exc
    if not isinstance(result, bytes):
        raise ReportRenderError("PDF renderer returned an invalid result")
    return result


def render_report(bundle: Mapping[str, Any], output_format: str) -> str | bytes:
    """Render *bundle* to ``markdown``, ``html``, or ``pdf``."""

    normalized = output_format.lower()
    if normalized in {"md", "markdown"}:
        return render_markdown(bundle)
    if normalized == "html":
        return render_html(bundle)
    if normalized == "pdf":
        return render_pdf(bundle)
    raise ReportRenderError("format must be one of: markdown, html, pdf")


def resolve_report_path(root: str | Path, destination: str | Path) -> Path:
    """Resolve a relative output path beneath *root*, rejecting symlinks."""

    relative = Path(destination)
    if relative.is_absolute() or not relative.name or any(part in {"", ".", ".."} for part in relative.parts):
        raise ReportRenderError("report output must be a non-empty relative path without traversal")
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)
    root_resolved = root_path.resolve(strict=True)
    if not root_resolved.is_dir():
        raise ReportRenderError("report root must be a directory")

    parent = root_resolved
    for part in relative.parts[:-1]:
        candidate = parent / part
        if os.path.lexists(candidate):
            mode = candidate.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise ReportRenderError("report output parent must not be a symlink")
            if not stat.S_ISDIR(mode):
                raise ReportRenderError("report output parent must be a directory")
        else:
            candidate.mkdir(mode=0o700)
        parent = candidate

    destination_path = parent / relative.name
    if os.path.lexists(destination_path) and stat.S_ISLNK(destination_path.lstat().st_mode):
        raise ReportRenderError("report output must not be a symlink")
    try:
        parent.resolve(strict=True).relative_to(root_resolved)
    except (OSError, ValueError) as exc:
        raise ReportRenderError("report output escapes the configured root") from exc
    return destination_path


def atomic_write_report(root: str | Path, destination: str | Path, content: str | bytes) -> Path:
    """Atomically write report content beneath a safe root."""

    output_path = resolve_report_path(root, destination)
    file_descriptor, temporary_name = tempfile.mkstemp(prefix=f".{output_path.name}.", dir=output_path.parent)
    temporary_path = Path(temporary_name)
    try:
        mode = "wb" if isinstance(content, bytes) else "w"
        kwargs = {} if isinstance(content, bytes) else {"encoding": "utf-8", "newline": "\n"}
        with os.fdopen(file_descriptor, mode, **kwargs) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, 0o600)
        # Recheck after writing so a swapped parent or destination cannot be
        # silently followed at commit time.
        checked_path = resolve_report_path(root, destination)
        if checked_path.parent.resolve(strict=True) != output_path.parent.resolve(strict=True):
            raise ReportRenderError("report output parent changed during write")
        os.replace(temporary_path, checked_path)
        return checked_path
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def write_report_bundle(
    bundle: Mapping[str, Any],
    output_format: str,
    root: str | Path,
    destination: str | Path,
) -> Path:
    """Validate, render, and atomically write a report bundle."""

    return atomic_write_report(root, destination, render_report(bundle, output_format))
