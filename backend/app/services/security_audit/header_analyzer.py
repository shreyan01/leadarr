"""Turns a raw response headers mapping into the hygiene fields
``SecurityFinding`` needs. Pure functions — headers dict in, structured
result out — no network I/O so they're fully unit-testable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class HeaderFindings:
    hsts: bool
    csp: str | None
    permissions_policy: str | None
    referrer_policy: str | None
    x_frame_options: str | None
    x_content_type_options: str | None
    server_header: str | None
    compression: str | None
    caching_headers: dict
    cookie_flags: list[dict] = field(default_factory=list)


def analyze_headers(headers: dict[str, str], set_cookie_values: list[str] | None = None) -> HeaderFindings:
    lower = {k.lower(): v for k, v in headers.items()}

    return HeaderFindings(
        hsts="strict-transport-security" in lower,
        csp=lower.get("content-security-policy"),
        permissions_policy=lower.get("permissions-policy"),
        referrer_policy=lower.get("referrer-policy"),
        x_frame_options=lower.get("x-frame-options"),
        x_content_type_options=lower.get("x-content-type-options"),
        server_header=lower.get("server"),
        compression=lower.get("content-encoding"),
        caching_headers={
            k: lower[k] for k in ("cache-control", "etag", "expires", "last-modified") if k in lower
        },
        cookie_flags=[analyze_cookie(c) for c in (set_cookie_values or [])],
    )


def analyze_cookie(set_cookie_value: str) -> dict:
    parts = [p.strip() for p in set_cookie_value.split(";")]
    name = parts[0].split("=", 1)[0] if parts else ""
    attrs = {p.lower() for p in parts[1:]}
    same_site_match = next((p for p in parts[1:] if p.lower().startswith("samesite=")), None)
    return {
        "name": name,
        "secure": "secure" in attrs,
        "http_only": "httponly" in attrs,
        "same_site": same_site_match.split("=", 1)[1] if same_site_match else None,
    }


def compute_hygiene_score(
    *,
    https: bool,
    header_findings: HeaderFindings,
    mixed_content: bool,
    directory_listing_exposed: bool,
    exposed_source_maps_count: int,
    exposed_config_files_count: int,
    exposed_secrets_count: int,
) -> int:
    """Weighted 0-100 hygiene score. Deliberately simple and auditable —
    each deduction maps to one concrete, explainable finding rather than a
    black-box heuristic, since this score ends up in a client-facing report.
    """
    score = 100
    if not https:
        score -= 25
    if not header_findings.hsts:
        score -= 8
    if not header_findings.csp:
        score -= 10
    if not header_findings.x_frame_options:
        score -= 6
    if not header_findings.x_content_type_options:
        score -= 4
    if not header_findings.referrer_policy:
        score -= 4
    if mixed_content:
        score -= 12
    if directory_listing_exposed:
        score -= 10
    score -= min(exposed_source_maps_count * 5, 15)
    score -= min(exposed_config_files_count * 15, 30)
    score -= min(exposed_secrets_count * 20, 40)
    insecure_cookies = [c for c in header_findings.cookie_flags if not c["secure"] or not c["http_only"]]
    score -= min(len(insecure_cookies) * 3, 12)
    return max(0, min(100, score))


_MIXED_CONTENT_PATTERN = re.compile(r"""url\((['"]?)(http://[^'")]+)\1\)|src=["'](http://[^"']+)["']""", re.I)


def detect_mixed_content(html: str, page_is_https: bool) -> bool:
    if not page_is_https:
        return False
    return bool(_MIXED_CONTENT_PATTERN.search(html))
