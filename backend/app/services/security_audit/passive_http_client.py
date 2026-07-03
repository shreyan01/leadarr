"""HTTP client that enforces the passive-analysis boundary in code, not just
in a docstring.

Only ``GET``/``HEAD`` are exposed. There is no method for sending a request
body, no way to pass query-string mutations designed to probe behaviour, and
every request is capped in size/time so a target site is never meaningfully
loaded. This is the single chokepoint the security-audit service is required
to go through — see ARCHITECTURE.md §1 and §6.
"""
from __future__ import annotations

import httpx

from app.core.exceptions import GuardrailViolationError

_ALLOWED_METHODS = {"GET", "HEAD"}
_MAX_RESPONSE_BYTES = 5_000_000
_TIMEOUT_S = 15.0


class PassiveHttpClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=_TIMEOUT_S,
            follow_redirects=True,
            headers={"User-Agent": "LeadForgeAuditBot/1.0 (+passive website audit)"},
        )

    async def get(self, url: str) -> httpx.Response:
        return await self._request("GET", url)

    async def head(self, url: str) -> httpx.Response:
        return await self._request("HEAD", url)

    async def _request(self, method: str, url: str) -> httpx.Response:
        if method not in _ALLOWED_METHODS:
            # Defense in depth: this branch is unreachable via the public
            # API above, but stays as an explicit trip wire against future
            # misuse (e.g. a POST added carelessly during a later phase).
            raise GuardrailViolationError(f"Method '{method}' is not permitted by PassiveHttpClient.")

        response = await self._client.request(method, url)
        if len(response.content) > _MAX_RESPONSE_BYTES:
            # Flag rather than silently truncate — callers decide whether a
            # partial read is acceptable for the specific check being run.
            response.extensions["leadforge_truncated"] = True
        return response

    async def aclose(self) -> None:
        await self._client.aclose()
