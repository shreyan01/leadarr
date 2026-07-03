"""Website validation — resolves the discovered URL, confirms it's live,
and does lightweight passive technology fingerprinting from response
headers and HTML markers. No login, no crawling beyond the homepage, no
active probing: this is the same guarded read-only posture as the
security-audit module, just used earlier in the pipeline to decide whether
a business's site is even worth auditing.
"""
from __future__ import annotations

import re
import socket
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx

_TECH_SIGNATURES: dict[str, list[re.Pattern]] = {
    "WordPress": [re.compile(r'name="generator" content="WordPress', re.I), re.compile(r"/wp-content/", re.I)],
    "Shopify": [re.compile(r"cdn\.shopify\.com", re.I), re.compile(r"Shopify\.theme", re.I)],
    "Wix": [re.compile(r"static\.wixstatic\.com", re.I), re.compile(r"wix\.com", re.I)],
    "Squarespace": [re.compile(r"squarespace\.com", re.I), re.compile(r"static1\.squarespace\.com", re.I)],
    "Webflow": [re.compile(r"webflow\.com", re.I), re.compile(r"data-wf-site", re.I)],
    "React": [re.compile(r"__NEXT_DATA__", re.I), re.compile(r"data-reactroot", re.I)],
    "Next.js": [re.compile(r"__NEXT_DATA__", re.I), re.compile(r"/_next/static/", re.I)],
    "Vue": [re.compile(r"__VUE__", re.I), re.compile(r"data-v-[a-f0-9]{8}", re.I)],
    "HubSpot": [re.compile(r"js\.hs-scripts\.com", re.I)],
    "GoDaddy Website Builder": [re.compile(r"godaddysites\.com", re.I)],
}

_SERVER_SIGNATURE = re.compile(r"^([A-Za-z\-]+)")


@dataclass
class ValidationResult:
    is_valid: bool
    final_url: str | None = None
    http_status: int | None = None
    redirect_chain: list[str] = field(default_factory=list)
    https: bool = False
    dns_resolved: bool = False
    resolved_ip: str | None = None
    server_header: str | None = None
    detected_technologies: list[str] = field(default_factory=list)
    error: str | None = None


class WebsiteValidationService:
    def __init__(self, timeout_s: float = 15.0) -> None:
        self._timeout_s = timeout_s

    async def validate(self, url: str) -> ValidationResult:
        normalized = self._normalize(url)
        if normalized is None:
            return ValidationResult(is_valid=False, error="Malformed URL")

        hostname = urlparse(normalized).hostname
        dns_resolved, resolved_ip = self._resolve_dns(hostname) if hostname else (False, None)
        if not dns_resolved:
            return ValidationResult(is_valid=False, dns_resolved=False, error="DNS resolution failed")

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_s, follow_redirects=True,
                headers={"User-Agent": "LeadForgeAuditBot/1.0 (+passive website audit)"},
            ) as client:
                response = await client.get(normalized)
        except httpx.HTTPError as exc:
            return ValidationResult(is_valid=False, dns_resolved=True, resolved_ip=resolved_ip, error=str(exc))

        redirect_chain = [str(r.url) for r in response.history] + [str(response.url)]
        html = response.text[:200_000]  # cap parse size — not a full crawl, just fingerprinting
        server_header = response.headers.get("server")

        return ValidationResult(
            is_valid=response.status_code < 400,
            final_url=str(response.url),
            http_status=response.status_code,
            redirect_chain=redirect_chain,
            https=str(response.url).startswith("https://"),
            dns_resolved=True,
            resolved_ip=resolved_ip,
            server_header=server_header,
            detected_technologies=self._detect_technologies(html, response.headers),
        )

    @staticmethod
    def _normalize(url: str) -> str | None:
        url = url.strip()
        if not url:
            return None
        if not re.match(r"^https?://", url, re.I):
            url = f"https://{url}"
        parsed = urlparse(url)
        if not parsed.hostname:
            return None
        return url

    @staticmethod
    def _resolve_dns(hostname: str) -> tuple[bool, str | None]:
        try:
            ip = socket.gethostbyname(hostname)
            return True, ip
        except socket.gaierror:
            return False, None

    @staticmethod
    def _detect_technologies(html: str, headers: httpx.Headers) -> list[str]:
        detected = []
        for tech, patterns in _TECH_SIGNATURES.items():
            if any(p.search(html) for p in patterns):
                detected.append(tech)

        powered_by = headers.get("x-powered-by")
        if powered_by:
            detected.append(f"X-Powered-By: {powered_by}")

        return sorted(set(detected))
