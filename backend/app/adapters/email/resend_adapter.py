from __future__ import annotations

import httpx

from app.adapters.email.interfaces import EmailSendResult
from app.core.exceptions import ProviderError

_RESEND_API_URL = "https://api.resend.com/emails"


class ResendEmailSender:
    def __init__(self, api_key: str, timeout_s: float = 20.0) -> None:
        self._api_key = api_key
        self._timeout_s = timeout_s

    async def send(
        self, *, to_address: str, from_address: str, subject: str, body_text: str, body_html: str | None = None
    ) -> EmailSendResult:
        payload = {
            "from": from_address,
            "to": [to_address],
            "subject": subject,
            "text": body_text,
            "html": body_html or f"<pre>{body_text}</pre>",
        }
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                response = await client.post(_RESEND_API_URL, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Resend send failed: {exc}") from exc

        return EmailSendResult(provider_message_id=data.get("id", ""), provider="resend")
