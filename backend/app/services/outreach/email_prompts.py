"""Builds the outreach-email generation prompt. Every specific claim the
model is allowed to make must trace back to the AI report already generated
for this audit — the prompt says so explicitly, matching the product
spec's "mention actual findings... never hallucinate" requirement.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from app.services.outreach.email_templates import get_template_instruction


@dataclass
class EmailInputs:
    business_name: str
    category: str
    sender_agency_name: str
    executive_summary: str
    top_improvements: list[dict]
    lead_score: float | None
    priority: str | None
    template_key: str


_EMAIL_JSON_SHAPE = {
    "subject": "<= 70 characters, specific, no clickbait/spam phrasing",
    "body_text": "plain-text email body, 120-200 words, professional tone, paragraphs separated by a blank line, ends with a soft call to action",
}


def build_email_prompt(inputs: EmailInputs) -> str:
    findings_block = json.dumps(
        {
            "executive_summary": inputs.executive_summary,
            "top_improvements": inputs.top_improvements[:5],
            "lead_score": inputs.lead_score,
            "priority": inputs.priority,
        },
        indent=2,
        default=str,
    )
    style_instruction = get_template_instruction(inputs.template_key)

    return (
        f"You are drafting a cold outreach email from \"{inputs.sender_agency_name}\", a web "
        f"agency, to \"{inputs.business_name}\" ({inputs.category}), based ONLY on the audit "
        "findings below. Do not invent statistics, dates, or claims not present in the data. "
        "Never use spammy language (no ALL CAPS, no excessive exclamation points, no "
        "\"act now\", no fake urgency). Reference at most 1-2 specific, concrete findings — "
        "do not list everything. End with a low-pressure call to action (e.g. offering a "
        f"quick call), not a hard sell.\n\n{style_instruction}\n\n"
        f"AUDIT FINDINGS:\n{findings_block}\n\n"
        "Respond with ONLY a single JSON object, no markdown fences, no prose outside the "
        f"JSON, matching exactly this shape:\n{json.dumps(_EMAIL_JSON_SHAPE, indent=2)}"
    )