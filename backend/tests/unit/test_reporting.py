from __future__ import annotations

import json

import pytest

from app.core.exceptions import ProviderError
from app.services.reporting.markdown_renderer import render_html, render_markdown
from app.services.reporting.report_parser import parse_report_response

VALID_REPORT = {
    "executive_summary": "The site loads slowly and has weak SEO fundamentals.",
    "technical_summary": "Lighthouse performance is 42/100 with a large LCP.",
    "business_summary": "Slow load times likely cost conversions.",
    "seo_summary": "Missing meta description and no structured data.",
    "accessibility_summary": "12 images are missing alt text.",
    "security_summary": "No HSTS header and no CSP configured.",
    "design_summary": "Dated layout with inconsistent spacing.",
    "top_improvements": [
        {"title": "Add HSTS header", "detail": "Enable strict transport security.", "category": "security"}
    ],
    "estimated_effort": {"Add HSTS header": "small"},
    "priority_fixes": ["Add HSTS header", "Compress hero image"],
    "estimated_business_impact": "Faster load times could meaningfully reduce bounce rate.",
}


class TestParseReportResponse:
    def test_parses_clean_json(self):
        result = parse_report_response(json.dumps(VALID_REPORT))
        assert result["executive_summary"] == VALID_REPORT["executive_summary"]
        assert result["top_improvements"][0]["title"] == "Add HSTS header"

    def test_strips_markdown_code_fences(self):
        fenced = "```json\n" + json.dumps(VALID_REPORT) + "\n```"
        result = parse_report_response(fenced)
        assert result["security_summary"] == VALID_REPORT["security_summary"]

    def test_raises_on_invalid_json(self):
        with pytest.raises(ProviderError):
            parse_report_response("not json at all")

    def test_raises_on_missing_required_section(self):
        incomplete = {k: v for k, v in VALID_REPORT.items() if k != "security_summary"}
        with pytest.raises(ProviderError):
            parse_report_response(json.dumps(incomplete))

    def test_missing_optional_fields_default_gracefully(self):
        minimal = {k: v for k, v in VALID_REPORT.items() if k not in ("top_improvements", "priority_fixes")}
        result = parse_report_response(json.dumps(minimal))
        assert result["top_improvements"] == []
        assert result["priority_fixes"] == []


class TestRenderMarkdown:
    def test_includes_business_name_and_score(self):
        parsed = parse_report_response(json.dumps(VALID_REPORT))
        md = render_markdown(business_name="Acme Roofing", report=parsed, lead_score=82.0, priority="critical")
        assert "Acme Roofing" in md
        assert "82" in md
        assert "Critical" in md

    def test_includes_all_sections(self):
        parsed = parse_report_response(json.dumps(VALID_REPORT))
        md = render_markdown(business_name="Acme Roofing", report=parsed, lead_score=None, priority=None)
        for heading in ["Executive Summary", "Technical Summary", "SEO", "Security Hygiene", "Priority Fixes"]:
            assert heading in md

    def test_html_rendering_produces_valid_tags(self):
        parsed = parse_report_response(json.dumps(VALID_REPORT))
        md = render_markdown(business_name="Acme Roofing", report=parsed, lead_score=82.0, priority="high")
        html = render_html(md)
        assert "<h1>" in html
        assert "<h2>" in html
