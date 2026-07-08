"""Checks same-origin links found on the page for broken (4xx/5xx)
responses. Uses PassiveHttpClient — HEAD requests only, same guardrail as
the security audit module, since checking whether a link resolves is
exactly the kind of passive read a browser or search crawler already does.
"""
from __future__ import annotations

from app.services.security_audit.passive_http_client import PassiveHttpClient


async def check_broken_links(client: PassiveHttpClient, links: list[str]) -> list[dict]:
    broken = []
    for url in links:
        try:
            response = await client.head(url)
            if response.status_code >= 400:
                broken.append({"url": url, "status": response.status_code})
        except Exception as exc:  # noqa: BLE001 — one unreachable link shouldn't abort the whole check
            broken.append({"url": url, "status": None, "error": str(exc)[:200]})
    return broken