from __future__ import annotations

from app.adapters.lighthouse_cli import parse_lighthouse_report

SAMPLE_LIGHTHOUSE_JSON = {
    "categories": {
        "performance": {"score": 0.83},
        "accessibility": {"score": 0.91},
        "seo": {"score": 1.0},
        "best-practices": {"score": 0.75},
    },
    "audits": {
        "largest-contentful-paint": {"numericValue": 2143.567},
        "cumulative-layout-shift": {"numericValue": 0.023},
        "speed-index": {"numericValue": 3011.2},
        "interactive": {"numericValue": 4500.0},
        "first-contentful-paint": {"numericValue": 1200.4},
    },
}


def test_parse_lighthouse_report_converts_category_scores_to_0_100():
    parsed = parse_lighthouse_report(SAMPLE_LIGHTHOUSE_JSON)
    assert parsed["performance_score"] == 83
    assert parsed["accessibility_score"] == 91
    assert parsed["seo_score"] == 100
    assert parsed["best_practices_score"] == 75


def test_parse_lighthouse_report_extracts_core_web_vitals():
    parsed = parse_lighthouse_report(SAMPLE_LIGHTHOUSE_JSON)
    assert parsed["lcp_ms"] == 2143.57
    assert parsed["cls"] == 0.02
    assert parsed["tti_ms"] == 4500.0


def test_parse_lighthouse_report_handles_missing_fields_gracefully():
    parsed = parse_lighthouse_report({"categories": {}, "audits": {}})
    assert parsed["performance_score"] is None
    assert parsed["lcp_ms"] is None
