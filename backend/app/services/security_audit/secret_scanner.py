"""Regex scanning of content the server already serves publicly (JS
bundles, config files it exposes). This never probes for anything hidden —
it only looks at bytes the site sent in response to a plain GET, checking
whether a secret was accidentally left in something meant to be public.
"""
from __future__ import annotations

import re

# (label, pattern) — deliberately high-precision patterns to avoid noisy
# false positives in a client-facing report.
_SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("AWS Access Key ID", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("AWS Secret Access Key (heuristic)", re.compile(r"aws_secret_access_key\s*[:=]\s*['\"][A-Za-z0-9/+=]{40}['\"]", re.I)),
    ("Google API Key", re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")),
    ("Stripe Live Secret Key", re.compile(r"\bsk_live_[0-9a-zA-Z]{24,}\b")),
    ("Slack Token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")),
    ("Generic Bearer/API Key Assignment", re.compile(r"(?:api_key|apikey|secret_key)\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}['\"]", re.I)),
    ("Private Key Block", re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----")),
]

_API_ENDPOINT_PATTERN = re.compile(
    r"""(?:fetch|axios\.\w+|XMLHttpRequest\(\)\.open)\s*\(\s*['"]([^'"]*/api/[^'"]*)['"]""", re.I
)


def scan_for_secrets(content: str, *, source: str) -> list[dict]:
    hits = []
    for label, pattern in _SECRET_PATTERNS:
        for match in pattern.finditer(content):
            hits.append({"type": label, "source": source, "match_preview": _redact(match.group(0))})
    return hits


def scan_for_public_api_endpoints(content: str) -> list[str]:
    return sorted({m.group(1) for m in _API_ENDPOINT_PATTERN.finditer(content)})


def _redact(value: str) -> str:
    """Never persist the actual secret value — only enough to identify the
    finding type for the report, so the audit itself doesn't become a new
    place the secret is stored in plaintext."""
    if len(value) <= 12:
        return "*" * len(value)
    return f"{value[:6]}...{'*' * 6}"
