from __future__ import annotations

import httpx

from app.adapters.email.interfaces import EmailSendResult
from app.core.exceptions import ProviderError

_SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"


class SendGridEmailSender:
    def __init__(self, api_key: str, timeout_s: float = 20.0) -> None:
        self._api_key = api_key
        self._timeout_s = timeout_s

    async def send(
        self, *, to_address: str, from_address: str, subject: str, body_text: str, body_html: str | None = None
    ) -> EmailSendResult:
        content = [{"type": "text/plain", "value": body_text}]
        if body_html:
            content.append({"type": "text/html", "value": body_html})

        payload = {
            "personalizations": [{"to": [{"email": to_address}]}],
            "from": {"email": from_address},
            "subject": subject,
            "content": content,
        }
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                response = await client.post(_SENDGRID_API_URL, json=payload, headers=headers)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"SendGrid send failed: {exc}") from exc

        # SendGrid returns the message id in the X-Message-Id response header, not the body.
        message_id = response.headers.get("X-Message-Id", "")
        return EmailSendResult(provider_message_id=message_id, provider="sendgrid")
