"""Validates the drafted email JSON and flags obvious spam-language
violations the prompt asked the model to avoid — a second, code-level check
rather than trusting the model's compliance alone."""
from __future__ import annotations

import json
import re

from app.core.exceptions import ProviderError

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_SPAM_PHRASES = ("act now", "limited time", "risk free", "100% guaranteed", "click here")


def parse_email_response(raw_text: str) -> dict:
    cleaned = _FENCE_RE.sub("", raw_text.strip())
    try:
        # strict=False tolerates raw control characters (a literal newline
        # instead of an escaped \n) inside JSON string values — smaller
        # local models occasionally do this even when the content itself
        # is otherwise perfectly valid; Python's default strict mode
        # rejects it as a technicality that has nothing to do with whether
        # the draft itself is usable.
        data = json.loads(cleaned, strict=False)
    except json.JSONDecodeError as exc:
        raise ProviderError(f"Email draft response was not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ProviderError("Email draft response JSON was not an object.")

    subject = str(data.get("subject") or "").strip()
    body_text = str(data.get("body_text") or "").strip()

    if not subject or not body_text:
        raise ProviderError("Email draft response missing subject or body_text.")

    spam_hits = detect_spam_language(f"{subject}\n{body_text}")
    if spam_hits:
        raise ProviderError(f"Email draft contains spam-like language: {', '.join(spam_hits)}")

    return {"subject": subject, "body_text": body_text}


def detect_spam_language(text: str) -> list[str]:
    lower = text.lower()
    hits = [phrase for phrase in _SPAM_PHRASES if phrase in lower]
    if _has_excessive_caps(text):
        hits.append("excessive capitalization")
    if text.count("!") > 2:
        hits.append("excessive exclamation points")
    return hits


def _has_excessive_caps(text: str) -> bool:
    words = re.findall(r"[A-Za-z]{4,}", text)
    shouting_words = [w for w in words if w.isupper()]
    return len(shouting_words) >= 2