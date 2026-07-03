"""Builds the report-generation prompt from real audit data only.

Every fact injected into the prompt comes from a DB row this run actually
produced (Lighthouse, security, accessibility, vision, business record) —
nothing is invented here, and the prompt explicitly instructs the model not
to state anything not grounded in the provided data, per the "never
hallucinate" requirement in the product spec.
"""
from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class ReportInputs:
    business_name: str
    category: str
    website_url: str
    lighthouse: dict
    security: dict
    accessibility: dict
    vision_summary: dict
    lead_score: float | None
    priority: str | None


_REPORT_JSON_SHAPE = {
    "executive_summary": "<= 4 sentences, written for a non-technical business owner",
    "technical_summary": "<= 5 sentences, written for a developer",
    "business_summary": "<= 3 sentences on what this means for the business",
    "seo_summary": "<= 3 sentences",
    "accessibility_summary": "<= 3 sentences",
    "security_summary": "<= 3 sentences, hygiene-only, no alarmist language",
    "design_summary": "<= 3 sentences",
    "top_improvements": [
        {"title": "short title", "detail": "1-2 sentences", "category": "performance|seo|security|accessibility|design"}
    ],
    "estimated_effort": {"<improvement title>": "small|medium|large"},
    "priority_fixes": ["title of the 3 highest-impact improvements, in order"],
    "estimated_business_impact": "<= 3 sentences on plausible business impact of fixing the top issues",
}


def build_report_prompt(inputs: ReportInputs) -> str:
    data_block = json.dumps(
        {
            "business_name": inputs.business_name,
            "category": inputs.category,
            "website_url": inputs.website_url,
            "lighthouse": inputs.lighthouse,
            "security_hygiene": inputs.security,
            "accessibility": inputs.accessibility,
            "visual_design": inputs.vision_summary,
            "lead_score": inputs.lead_score,
            "priority": inputs.priority,
        },
        indent=2,
        default=str,
    )

    return (
        "You are writing a website-audit report for a sales agency to send to "
        f"a prospective client, \"{inputs.business_name}\" ({inputs.category}). "
        "Use ONLY the data below — do not invent findings, statistics, or "
        "claims not supported by it. If a section has no supporting data, say "
        "so briefly rather than fabricating detail. Keep language professional, "
        "specific, and never alarmist or spammy — this becomes part of an "
        "outreach email.\n\n"
        f"AUDIT DATA:\n{data_block}\n\n"
        "Respond with ONLY a single JSON object, no markdown fences, no prose "
        "outside the JSON, matching exactly this shape (types/lengths shown as "
        f"guidance, not literal values):\n{json.dumps(_REPORT_JSON_SHAPE, indent=2)}"
    )
