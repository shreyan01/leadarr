"""Validates and clamps the vision model's structured response into the
fields ``VisionAnalysis`` needs. Pure function — dict in, dict out — so
it's testable against hand-built fixtures without calling a model.
"""
from __future__ import annotations

_SCORE_FIELDS = [
    "trust",
    "professionalism",
    "modernity",
    "whitespace",
    "typography",
    "layout",
    "visual_hierarchy",
    "cta",
    "conversion",
    "brand_consistency",
    "nav_clarity",
    "mobile_friendliness",
    "overall",
]

_FIELD_TO_COLUMN = {
    "trust": "trust_score",
    "professionalism": "professionalism_score",
    "modernity": "modernity_score",
    "whitespace": "whitespace_score",
    "typography": "typography_score",
    "layout": "layout_score",
    "visual_hierarchy": "visual_hierarchy_score",
    "cta": "cta_score",
    "conversion": "conversion_score",
    "brand_consistency": "brand_consistency_score",
    "nav_clarity": "nav_clarity_score",
    "mobile_friendliness": "mobile_friendliness_score",
    "overall": "overall_score",
}


def parse_vision_scores(structured: dict) -> dict:
    """Returns a dict keyed by the VisionAnalysis column names, with every
    score clamped to [0, 100] and missing/non-numeric values coerced to
    None rather than raising — a malformed field shouldn't fail the whole
    audit stage."""
    result: dict[str, int | None] = {}
    for field, column in _FIELD_TO_COLUMN.items():
        result[column] = _clamp_score(structured.get(field))

    if result["overall_score"] is None:
        computed = [v for k, v in result.items() if k != "overall_score" and v is not None]
        result["overall_score"] = round(sum(computed) / len(computed)) if computed else None

    return result


def _clamp_score(value) -> int | None:
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    return max(0, min(100, score))
