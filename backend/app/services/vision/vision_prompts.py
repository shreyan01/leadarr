"""Builds the prompt sent to the vision model for one screenshot.

Kept as a pure string-building function (no I/O) so prompt changes are
easy to review/test independently of the provider call.
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

VISION_JSON_SCHEMA_HINT = "{" + ", ".join(f'"{f}": <0-100 integer>' for f in _SCORE_FIELDS) + ', "notes": "<= 3 short sentences of specific, concrete observations"}'


def build_vision_prompt(*, business_name: str, device: str) -> str:
    return (
        f"You are a website design auditor evaluating the {device} screenshot of "
        f"the small-business website for \"{business_name}\". Score each dimension "
        "from 0 (very poor) to 100 (excellent) based ONLY on what is visible in the "
        "image — do not guess at things you cannot see. Dimensions: trust "
        "(does it look credible/legitimate), professionalism, modernity (vs. "
        "outdated design), whitespace usage, typography quality, layout quality, "
        "visual hierarchy (is the most important content emphasized), call-to-action "
        "clarity, conversion optimization, brand consistency, navigation clarity, "
        f"mobile friendliness (judge from what's visible in this {device} view), and "
        "an overall score. Respond with ONLY a single JSON object, no markdown "
        "fences, no prose outside the JSON, in exactly this shape:\n"
        f"{VISION_JSON_SCHEMA_HINT}"
    )
