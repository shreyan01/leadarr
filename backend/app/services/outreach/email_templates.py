"""Named outreach templates. Each is a *framing instruction* injected into
the same underlying prompt builder — not a fill-in-the-blank string
template — so the model still grounds specifics in real audit data
regardless of which framing is chosen.
"""
from __future__ import annotations

TEMPLATES: dict[str, str] = {
    "default": (
        "Write a warm, consultative outreach email. Lead with a genuine, "
        "specific observation about their business, then transition to one "
        "or two concrete website findings."
    ),
    "direct": (
        "Write a short, direct outreach email. State the single most "
        "impactful finding in the first sentence and get to the ask quickly."
    ),
    "educational": (
        "Write an educational outreach email that briefly explains *why* the "
        "top finding matters for their business (e.g. lost visitors, lower "
        "search ranking) before making the ask."
    ),
}

DEFAULT_TEMPLATE_KEY = "default"


def get_template_instruction(template_key: str) -> str:
    return TEMPLATES.get(template_key, TEMPLATES[DEFAULT_TEMPLATE_KEY])
