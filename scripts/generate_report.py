#!/usr/bin/env python3
"""
Generate professional PDF audit report from markdown audit results.

Produces a client-ready PDF with health score gauge, platform bar charts,
pass/fail distribution chart, formatted tables, and zero overlap.

Usage:
    python generate_report.py audit-results.md
    python generate_report.py audit-results.md --output report.pdf
    python generate_report.py audit-results.md --brand "Client Name"

Dependencies:
    pip install reportlab matplotlib
"""

import argparse
import html
import json
import logging
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from url_utils import resolve_output_path, sanitize_error

# Version stamp shown in PDF header/footer. Keep in sync with
# .claude-plugin/plugin.json `version`.
__version__ = "2.0.1"

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, Image, KeepTogether
    )
except ImportError:
    print("Error: reportlab required. Install with: pip install reportlab")
    sys.exit(1)

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

logger = logging.getLogger("generate_report")

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

C_PRIMARY = colors.HexColor("#1a1a2e")
C_ACCENT = colors.HexColor("#0f3460")
C_PASS = colors.HexColor("#16a34a")
C_WARN = colors.HexColor("#f59e0b")
C_FAIL = colors.HexColor("#dc2626")
C_LIGHT = colors.HexColor("#f8fafc")
C_ROW_ALT = colors.HexColor("#f1f5f9")
C_HEADER = colors.HexColor("#1e293b")

GRADE_COLORS = {
    "A": "#16a34a", "B": "#22c55e", "C": "#f59e0b",
    "D": "#f97316", "F": "#dc2626",
}

# Try to register Times New Roman; fall back to Times-Roman (built-in)
BODY_FONT = "Times-Roman"
BODY_BOLD = "Times-Bold"
HEAD_FONT = "Helvetica-Bold"
for path in [
    "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    "C:/Windows/Fonts/times.ttf",
]:
    if os.path.exists(path):
        try:
            pdfmetrics.registerFont(TTFont("TimesNewRoman", path))
            BODY_FONT = "TimesNewRoman"
            break
        except Exception:
            pass

PAGE_WIDTH = 7.0 * inch  # letter minus margins
MAX_IMG_W = 6.5 * inch
MAX_IMG_H = 4.0 * inch

# Sections already rendered in the header area (skip as body sections)
SKIP_SECTIONS = {"executive summary", "critical issues", "quick wins"}


# ---------------------------------------------------------------------------
# Markdown to HTML converter (for reportlab Paragraph)
# ---------------------------------------------------------------------------

def _md_to_html(text: str) -> str:
    """Escape untrusted text, then add a constrained set of ReportLab tags."""
    text = html.escape(str(text), quote=True)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    text = re.sub(r"`(.+?)`", r"<font face='Courier' size='9'>\1</font>", text)
    return text


# ---------------------------------------------------------------------------
# Markdown Parser (state machine)
# ---------------------------------------------------------------------------

def parse_markdown(filepath: str) -> dict:
    """Parse audit results markdown into structured data."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    data = {
        "title": "",
        "health_score": None,
        "grade": "",
        "platform_scores": {},
        "critical_issues": [],
        "high_issues": [],
        "quick_wins": [],
        "sections": [],
        "tables": [],
        "result_counts": {"Pass": 0, "Warning": 0, "Fail": 0},
    }

    lines = content.split("\n")
    section_title = None
    section_items = []
    in_table = False
    table_rows = []
    table_headers = []

    for line in lines:
        stripped = line.strip()

        # Title
        if line.startswith("# ") and not data["title"]:
            data["title"] = line[2:].strip()
            continue

        # Health score
        m = re.search(r"(?:Ads\s+)?Health\s+Score[:\s]*(\d+)\s*/\s*100", line, re.I)
        if m:
            data["health_score"] = int(m.group(1))

        # Grade
        m = re.search(r"Grade[:\s]*([A-F])\b", line)
        if m:
            data["grade"] = m.group(1)

        # Platform scores: handle both "Google Ads: 78/100" and table rows
        # Use a pattern that can cross table pipes
        m = re.search(
            r"(Google|Meta|LinkedIn|TikTok|Microsoft|Apple|YouTube)"
            r".*?(\d{1,3})\s*/\s*100",
            line, re.I
        )
        if m:
            data["platform_scores"][m.group(1)] = int(m.group(2))

        # Count Pass/Warning/Fail results from table rows
        if stripped.startswith("|"):
            lower = stripped.lower()
            if "| pass" in lower or "| pass |" in lower:
                data["result_counts"]["Pass"] += 1
            if "| warning" in lower or "| warning |" in lower:
                data["result_counts"]["Warning"] += 1
            if "| fail" in lower or "| fail |" in lower:
                data["result_counts"]["Fail"] += 1

        # Critical / High issues
        if stripped.startswith("- "):
            text = stripped.lstrip("- ").strip()
            if "Critical" in line:
                data["critical_issues"].append(text)
            elif "High" in line and section_title and "high" in section_title.lower():
                data["high_issues"].append(text)

        # Quick wins
        if re.match(r"^[\d]+\.\s", stripped) and section_title and "quick win" in (section_title or "").lower():
            data["quick_wins"].append(re.sub(r"^\d+\.\s*", "", stripped))
        elif stripped.startswith("- ") and section_title and "quick win" in (section_title or "").lower():
            data["quick_wins"].append(stripped.lstrip("- ").strip())

        # Table detection
        if stripped.startswith("|") and not re.match(r"^\|[\s\-:|]+\|$", stripped):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if not in_table:
                in_table = True
                table_headers = cells
                table_rows = []
            else:
                table_rows.append(cells)
            continue
        elif stripped.startswith("|") and re.match(r"^\|[\s\-:|]+\|$", stripped):
            continue  # separator row
        else:
            if in_table and table_headers:
                section_items.append({
                    "type": "table",
                    "headers": table_headers,
                    "rows": table_rows,
                })
                data["tables"].append({"headers": table_headers, "rows": table_rows})
                in_table = False
                table_headers = []
                table_rows = []

        # Section tracking
        if line.startswith("## "):
            if section_title is not None:
                _flush_section(data, section_title, section_items)
            section_title = line[3:].strip()
            section_items = []
        elif line.startswith("### "):
            section_items.append({"type": "subtitle", "text": line[4:].strip()})
        elif stripped.startswith("- "):
            section_items.append({"type": "bullet", "text": stripped.lstrip("- ").strip()})
        elif stripped and not stripped.startswith("#"):
            section_items.append({"type": "text", "text": stripped})

    if section_title is not None:
        if in_table and table_headers:
            section_items.append({"type": "table", "headers": table_headers, "rows": table_rows})
        _flush_section(data, section_title, section_items)

    return data


def _flush_section(data, title, items):
    """Add section only if it has meaningful content and is not a duplicate."""
    if title.lower().strip() in SKIP_SECTIONS:
        logger.info(f"Skipped duplicate section: '{title}' (already rendered in header)")
        return
    meaningful = [i for i in items if i.get("text") or i.get("type") == "table"]
    if meaningful:
        data["sections"].append({"title": title, "items": items})
    else:
        logger.warning(f"Skipped empty section: '{title}'")


# ---------------------------------------------------------------------------
# Chart Generators (matplotlib)
# ---------------------------------------------------------------------------

def build_gauge_chart(score: int, grade: str) -> str | None:
    """Build health score donut gauge chart, return temp PNG path."""
    if not HAS_MATPLOTLIB:
        return None

    color = GRADE_COLORS.get(grade, "#64748b")
    bg = "#e2e8f0"

    fig, ax = plt.subplots(figsize=(3, 3), subplot_kw={"projection": "polar"})
    fig.patch.set_facecolor("white")

    theta = 2 * math.pi * (score / 100)
    ax.barh(1, theta, height=0.6, color=color, alpha=0.9)
    ax.barh(1, 2 * math.pi - theta, left=theta, height=0.6, color=bg, alpha=0.4)
    ax.set_ylim(0, 2)
    ax.set_axis_off()
    ax.text(0, 0, f"{score}", ha="center", va="center", fontsize=28,
            fontweight="bold", color=color, transform=ax.transAxes)
    ax.text(0, -0.15, f"Grade {grade}", ha="center", va="center",
            fontsize=12, color="#475569", transform=ax.transAxes)

    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    fig.savefig(path, dpi=150, bbox_inches="tight", transparent=False)
    plt.close(fig)
    return path


def build_platform_chart(platform_scores: dict) -> str | None:
    """Build horizontal bar chart of platform scores, return temp PNG path."""
    if not HAS_MATPLOTLIB or not platform_scores:
        return None

    platforms = list(platform_scores.keys())
    scores = list(platform_scores.values())
    bar_colors = []
    for s in scores:
        if s >= 90:
            bar_colors.append("#16a34a")
        elif s >= 75:
            bar_colors.append("#22c55e")
        elif s >= 60:
            bar_colors.append("#f59e0b")
        else:
            bar_colors.append("#dc2626")

    fig, ax = plt.subplots(figsize=(5, max(2, len(platforms) * 0.7)))
    fig.patch.set_facecolor("white")
    bars = ax.barh(platforms, scores, color=bar_colors, height=0.5, edgecolor="white")
    ax.set_xlim(0, 100)
    ax.set_xlabel("Health Score", fontsize=9, color="#475569")
    ax.tick_params(axis="y", labelsize=9)
    ax.tick_params(axis="x", labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for bar, s in zip(bars, scores):
        ax.text(bar.get_width() + 1.5, bar.get_y() + bar.get_height() / 2,
                f"{s}", va="center", fontsize=9, fontweight="bold", color="#334155")

    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def build_result_distribution_chart(result_counts: dict) -> str | None:
    """Build pass/warning/fail donut chart from audit results."""
    if not HAS_MATPLOTLIB:
        return None
    total = sum(result_counts.values())
    if total == 0:
        return None

    labels = []
    sizes = []
    chart_colors = []
    color_map = {"Pass": "#16a34a", "Warning": "#f59e0b", "Fail": "#dc2626"}

    for label in ["Pass", "Warning", "Fail"]:
        count = result_counts.get(label, 0)
        if count > 0:
            labels.append(f"{label} ({count})")
            sizes.append(count)
            chart_colors.append(color_map[label])

    fig, ax = plt.subplots(figsize=(3.5, 3))
    fig.patch.set_facecolor("white")
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=chart_colors, autopct="%1.0f%%",
        startangle=90, pctdistance=0.75, wedgeprops={"width": 0.4, "edgecolor": "white"},
        textprops={"fontsize": 8}
    )
    for at in autotexts:
        at.set_fontsize(8)
        at.set_fontweight("bold")
        at.set_color("white")
    ax.set_title("Check Results Distribution", fontsize=10, fontweight="bold",
                 color="#1e293b", pad=10)

    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def render_mermaid(mermaid_code: str) -> str | None:
    """Render mermaid diagram to PNG if mmdc is available."""
    mmdc = shutil.which("mmdc")
    if not mmdc:
        return None
    try:
        fd_src, src = tempfile.mkstemp(suffix=".mmd")
        os.close(fd_src)
        fd_out, out = tempfile.mkstemp(suffix=".png")
        os.close(fd_out)
        with open(src, "w") as f:
            f.write(mermaid_code)
        subprocess.run([mmdc, "-i", src, "-o", out, "-b", "white", "-w", "600"],
                       capture_output=True, timeout=15)
        if os.path.exists(out) and os.path.getsize(out) > 0:
            return out
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# PDF Builder
# ---------------------------------------------------------------------------

def _make_styles():
    """Create professional styles with proper spacing to prevent overlap."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle("RTitle", fontName=HEAD_FONT, fontSize=22,
                              textColor=C_PRIMARY, spaceAfter=2, alignment=TA_LEFT))
    styles.add(ParagraphStyle("RSubtitle", fontName=BODY_FONT, fontSize=10,
                              textColor=colors.HexColor("#64748b"),
                              spaceBefore=2, spaceAfter=10))
    styles.add(ParagraphStyle("RSectionHead", fontName=HEAD_FONT, fontSize=14,
                              textColor=C_ACCENT, spaceBefore=14, spaceAfter=6))
    styles.add(ParagraphStyle("RSubHead", fontName=HEAD_FONT, fontSize=11,
                              textColor=C_PRIMARY, spaceBefore=8, spaceAfter=3))
    styles.add(ParagraphStyle("RBody", fontName=BODY_FONT, fontSize=10,
                              leading=14, spaceAfter=4))
    styles.add(ParagraphStyle("RBullet", fontName=BODY_FONT, fontSize=10,
                              leading=14, leftIndent=18, bulletIndent=8,
                              spaceAfter=3))
    styles.add(ParagraphStyle("RCaption", fontName=BODY_FONT, fontSize=8,
                              textColor=colors.HexColor("#64748b"),
                              alignment=TA_CENTER, spaceBefore=2, spaceAfter=10))
    styles.add(ParagraphStyle("RFooter", fontName=BODY_FONT, fontSize=7,
                              textColor=colors.HexColor("#94a3b8"),
                              alignment=TA_CENTER))
    return styles


def _wrap_cell(text, style):
    """Wrap cell text in a Paragraph to prevent overflow and render markdown."""
    if not isinstance(text, str):
        text = str(text)
    text = _md_to_html(text)
    if len(text) > 50:
        return Paragraph(text, style)
    return Paragraph(text, style)


def _build_table(headers: list, rows: list, col_widths=None) -> Table:
    """Build a formatted Table with word-wrapped cells and alternating rows."""
    wrap_style = ParagraphStyle("CellWrap", fontName=BODY_FONT, fontSize=8,
                                leading=10, wordWrap="CJK")
    header_wrap = ParagraphStyle("HeaderWrap", fontName=HEAD_FONT, fontSize=8,
                                 leading=10, textColor=colors.white, wordWrap="CJK")

    wrapped_headers = [_wrap_cell(h, header_wrap) for h in headers]
    wrapped_rows = [[_wrap_cell(c, wrap_style) for c in row] for row in rows]

    all_rows = [wrapped_headers] + wrapped_rows
    if col_widths is None:
        n = len(headers)
        if n <= 3:
            col_widths = [PAGE_WIDTH / n] * n
        elif n == 4:
            col_widths = [PAGE_WIDTH * 0.10, PAGE_WIDTH * 0.30,
                          PAGE_WIDTH * 0.12, PAGE_WIDTH * 0.48]
        elif n == 5:
            col_widths = [PAGE_WIDTH * 0.08, PAGE_WIDTH * 0.25,
                          PAGE_WIDTH * 0.12, PAGE_WIDTH * 0.12, PAGE_WIDTH * 0.43]
        else:
            first_col = PAGE_WIDTH * 0.08
            remaining = (PAGE_WIDTH - first_col) / (n - 1)
            col_widths = [first_col] + [remaining] * (n - 1)

    tbl = Table(all_rows, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), C_HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), HEAD_FONT),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTNAME", (0, 1), (-1, -1), BODY_FONT),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    for i in range(1, len(all_rows)):
        if i % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), C_ROW_ALT))

    tbl.setStyle(TableStyle(style_cmds))
    return tbl


def _add_page_footer(canvas, doc):
    """Add footer with page number and branding on every page."""
    canvas.saveState()
    canvas.setFont(BODY_FONT, 7)
    canvas.setFillColor(colors.HexColor("#94a3b8"))
    canvas.drawCentredString(
        letter[0] / 2, 0.4 * inch,
        f"claude-ads v{__version__}  |  Page {doc.page}  |  {datetime.now().strftime('%B %d, %Y')}"
    )
    canvas.restoreState()


def build_pdf(data: dict, output_path: str, brand_name: str = ""):
    """Build the complete professional PDF report."""
    output_path = str(resolve_output_path(output_path, create_parent=True))
    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        rightMargin=0.75 * inch, leftMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
    )
    styles = _make_styles()
    elements = []
    temp_files = []

    # --- Title Page Header ---
    title = brand_name or data.get("title", "Ad Account Audit Report")
    elements.append(Paragraph(_md_to_html(title), styles["RTitle"]))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(
        f"Generated {datetime.now().strftime('%B %d, %Y')}  |  Powered by claude-ads v{__version__}",
        styles["RSubtitle"],
    ))
    elements.append(HRFlowable(width="100%", thickness=2, color=C_ACCENT))
    elements.append(Spacer(1, 12))

    # --- Charts Row: Gauge + Platform Bar (side by side) ---
    score = data.get("health_score")
    grade = data.get("grade", "")

    gauge_path = build_gauge_chart(score, grade) if score is not None else None
    platform_path = build_platform_chart(data.get("platform_scores", {}))

    if gauge_path and platform_path:
        temp_files.extend([gauge_path, platform_path])
        ph = min(max(1.8, len(data["platform_scores"]) * 0.55) * inch, MAX_IMG_H)
        chart_row = [
            Image(gauge_path, width=2.2 * inch, height=2.2 * inch),
            Image(platform_path, width=4.3 * inch, height=ph),
        ]
        chart_table = Table([chart_row], colWidths=[2.7 * inch, 4.3 * inch])
        chart_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, 0), "CENTER"),
            ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ]))
        elements.append(chart_table)
        elements.append(Paragraph(
            f"Fig 1: Health Score {score}/100 (Grade {grade})"
            f"  |  Fig 2: Platform Score Comparison",
            styles["RCaption"],
        ))
    elif gauge_path:
        temp_files.append(gauge_path)
        elements.append(Image(gauge_path, width=2.5 * inch, height=2.5 * inch))
        elements.append(Paragraph(
            f"Fig 1: Health Score {score}/100 (Grade {grade})", styles["RCaption"]))
    elif score is not None:
        grade_color = colors.HexColor(GRADE_COLORS.get(grade, "#64748b"))
        score_tbl = Table(
            [["Ads Health Score", f"{score}/100", f"Grade: {grade}"]],
            colWidths=[3 * inch, 2 * inch, 2 * inch],
        )
        score_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_LIGHT),
            ("TEXTCOLOR", (1, 0), (2, 0), grade_color),
            ("FONTNAME", (0, 0), (-1, -1), HEAD_FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 14),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOX", (0, 0), (-1, -1), 1, C_ACCENT),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        elements.append(score_tbl)
        elements.append(Spacer(1, 8))

    # --- Result Distribution Chart (pass/warning/fail donut) ---
    dist_path = build_result_distribution_chart(data.get("result_counts", {}))
    if dist_path:
        temp_files.append(dist_path)
        elements.append(Spacer(1, 4))
        elements.append(Image(dist_path, width=3.0 * inch, height=2.5 * inch))
        elements.append(Paragraph("Fig 3: Audit Check Results Distribution", styles["RCaption"]))

    # --- Critical Issues ---
    if data.get("critical_issues"):
        elements.append(Spacer(1, 4))
        elements.append(Paragraph("Critical Issues", styles["RSectionHead"]))
        for issue in data["critical_issues"][:10]:
            elements.append(Paragraph(
                f"\u2022 {_md_to_html(issue)}", styles["RBullet"]))

    # --- Quick Wins ---
    if data.get("quick_wins"):
        elements.append(Spacer(1, 4))
        elements.append(Paragraph("Quick Wins (Do This Week)", styles["RSectionHead"]))
        for i, win in enumerate(data["quick_wins"][:7], 1):
            elements.append(Paragraph(
                f"{i}. {_md_to_html(win)}", styles["RBullet"]))

    # --- Body Sections ---
    for idx, section in enumerate(data.get("sections", [])):
        items = section.get("items", [])
        meaningful = [i for i in items if i.get("text") or i.get("type") == "table"]
        if not meaningful:
            continue

        # Section divider
        elements.append(Spacer(1, 6))
        elements.append(HRFlowable(width="100%", thickness=0.5,
                                   color=colors.HexColor("#e2e8f0")))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(_md_to_html(section["title"]), styles["RSectionHead"]))

        for item in items:
            itype = item.get("type", "")
            if itype == "subtitle":
                elements.append(Paragraph(
                    _md_to_html(item["text"]), styles["RSubHead"]))
            elif itype == "bullet":
                elements.append(Paragraph(
                    f"\u2022 {_md_to_html(item['text'])}", styles["RBullet"]))
            elif itype == "text":
                elements.append(Paragraph(
                    _md_to_html(item["text"]), styles["RBody"]))
            elif itype == "table":
                headers = item.get("headers", [])
                rows = item.get("rows", [])
                if headers and rows:
                    tbl = _build_table(headers, rows)
                    elements.append(KeepTogether([
                        Spacer(1, 4), tbl, Spacer(1, 6)
                    ]))

    # --- End Footer ---
    elements.append(Spacer(1, 16))
    elements.append(HRFlowable(width="100%", thickness=1, color=C_ACCENT))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        f"Report generated by claude-ads v{__version__}  |  "
        "https://github.com/AgriciDaniel/claude-ads",
        styles["RFooter"],
    ))

    doc.build(elements, onFirstPage=_add_page_footer, onLaterPages=_add_page_footer)

    for f in temp_files:
        try:
            os.unlink(f)
        except OSError:
            pass

    return output_path


# ---------------------------------------------------------------------------
# Content Quality Checker (guardrail)
# ---------------------------------------------------------------------------

def check_content(data: dict) -> list:
    """Validate report content quality, layout safety, and formatting."""
    warnings = []

    # Content completeness
    if data["health_score"] is None:
        warnings.append("LAYOUT: No health score found (gauge chart will be missing)")
    if not data["grade"]:
        warnings.append("LAYOUT: No grade found (gauge chart label missing)")
    if not data.get("platform_scores"):
        warnings.append("LAYOUT: No platform scores found (bar chart will be missing)")
    if not data["critical_issues"] and not data["sections"]:
        warnings.append("CONTENT: No critical issues or sections found. Report may be empty")

    # Section quality
    for section in data["sections"]:
        items = section.get("items", [])
        meaningful = [it for it in items if it.get("text") or it.get("type") == "table"]
        if len(meaningful) < 2:
            warnings.append(
                f"CONTENT: Section '{section['title']}' has <2 items (may look sparse)")

    # Empty tables
    empty_tables = sum(1 for t in data["tables"] if not t["rows"])
    if empty_tables:
        warnings.append(f"LAYOUT: {empty_tables} empty table(s) (headers only, no data)")

    # Overflow risk: tables with too many columns
    for t in data["tables"]:
        ncols = len(t.get("headers", []))
        if ncols > 6:
            warnings.append(
                f"LAYOUT: Table with {ncols} columns may overflow. Consider splitting")

    # Raw markdown syntax check (would render as literal ** in PDF)
    for section in data["sections"]:
        for item in section.get("items", []):
            text = item.get("text", "")
            if "**" in text and item.get("type") != "table":
                # This is expected and will be converted by _md_to_html
                pass

    # Result distribution check
    total = sum(data.get("result_counts", {}).values())
    if total == 0:
        warnings.append("CHART: No Pass/Warning/Fail results detected (distribution chart will be empty)")

    return warnings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate professional PDF audit report from markdown results"
    )
    parser.add_argument("input", help="Path to audit results markdown file")
    parser.add_argument("--output", "-o", default=None,
                        help="Output PDF path (default: <input>-report.pdf)")
    parser.add_argument("--brand", "-b", default="",
                        help="Brand/client name for report header")
    parser.add_argument("--json", action="store_true",
                        help="Output parsed data as JSON instead of PDF")
    parser.add_argument("--check", action="store_true",
                        help="Run content quality checker and print warnings")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose logging")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if not os.path.exists(args.input):
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    data = parse_markdown(args.input)

    if args.check:
        warnings = check_content(data)
        if warnings:
            for w in warnings:
                print(f"WARNING: {w}")
            print(f"\n{len(warnings)} warning(s) found.")
        else:
            print("Content check PASSED: no issues found.")
        return

    if args.json:
        print(json.dumps(data, indent=2, default=str))
        return

    output_path = args.output or f"{Path(args.input).stem}-report.pdf"
    try:
        output_path = build_pdf(data, output_path, args.brand)
    except ValueError as exc:
        print(f"Error: {sanitize_error(exc)}", file=sys.stderr)
        sys.exit(1)
    print(f"PDF report generated: {output_path}")

    # Auto-run content check post-build
    warnings = check_content(data)
    if warnings:
        print(f"\nContent warnings ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")


if __name__ == "__main__":
    main()
