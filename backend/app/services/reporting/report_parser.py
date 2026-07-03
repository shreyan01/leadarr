"""Parses and validates the LLM's report JSON. Handles the common failure
modes of LLM structured output (fenced code blocks, missing optional keys)
without ever inventing content the model didn't provide.
"""
from __future__ import annotations

import json
import re

from app.core.exceptions import ProviderError

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

_REQUIRED_KEYS = (
    "executive_summary",
    "technical_summary",
    "business_summary",
    "seo_summary",
    "accessibility_summary",
    "security_summary",
    "design_summary",
)


def parse_report_response(raw_text: str) -> dict:
    cleaned = _FENCE_RE.sub("", raw_text.strip())
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ProviderError(f"AI report response was not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ProviderError("AI report response JSON was not an object.")

    missing = [k for k in _REQUIRED_KEYS if not data.get(k)]
    if missing:
        raise ProviderError(f"AI report response missing required section(s): {', '.join(missing)}")

    return {
        "executive_summary": str(data["executive_summary"]).strip(),
        "technical_summary": str(data["technical_summary"]).strip(),
        "business_summary": str(data["business_summary"]).strip(),
        "seo_summary": str(data["seo_summary"]).strip(),
        "accessibility_summary": str(data["accessibility_summary"]).strip(),
        "security_summary": str(data["security_summary"]).strip(),
        "design_summary": str(data["design_summary"]).strip(),
        "top_improvements": data.get("top_improvements") or [],
        "estimated_effort": data.get("estimated_effort") or {},
        "priority_fixes": data.get("priority_fixes") or [],
        "estimated_business_impact": str(data.get("estimated_business_impact") or "").strip(),
    }
