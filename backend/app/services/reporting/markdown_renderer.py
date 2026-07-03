"""Turns the validated report dict into Markdown (source of truth) and HTML
(rendered from the Markdown, not generated separately, so the two can never
drift apart)."""
from __future__ import annotations

import markdown as markdown_lib


def render_markdown(*, business_name: str, report: dict, lead_score: float | None, priority: str | None) -> str:
    lines = [f"# Website Audit Report — {business_name}", ""]

    if lead_score is not None:
        lines += [f"**Lead Score:** {lead_score:.0f}/100  **Priority:** {(priority or 'n/a').title()}", ""]

    sections = [
        ("Executive Summary", report["executive_summary"]),
        ("Business Impact", report.get("business_summary", "")),
        ("Technical Summary", report["technical_summary"]),
        ("SEO", report["seo_summary"]),
        ("Accessibility", report["accessibility_summary"]),
        ("Security Hygiene", report["security_summary"]),
        ("Design", report["design_summary"]),
    ]
    for heading, body in sections:
        if body:
            lines += [f"## {heading}", "", body, ""]

    top_improvements = report.get("top_improvements") or []
    if top_improvements:
        lines += ["## Top Improvements", ""]
        effort_map = report.get("estimated_effort") or {}
        for item in top_improvements:
            title = item.get("title", "Untitled")
            detail = item.get("detail", "")
            category = item.get("category", "")
            effort = effort_map.get(title, "")
            suffix = " ".join(
                p for p in [f"_{category}_" if category else "", f"(effort: {effort})" if effort else ""] if p
            )
            lines.append(f"- **{title}** — {detail} {suffix}".rstrip())
        lines.append("")

    priority_fixes = report.get("priority_fixes") or []
    if priority_fixes:
        lines += ["## Priority Fixes", ""]
        lines += [f"{i + 1}. {fix}" for i, fix in enumerate(priority_fixes)]
        lines.append("")

    if report.get("estimated_business_impact"):
        lines += ["## Estimated Business Impact", "", report["estimated_business_impact"], ""]

    return "\n".join(lines).strip() + "\n"


def render_html(markdown_text: str) -> str:
    return markdown_lib.markdown(markdown_text, extensions=["extra", "sane_lists"])
