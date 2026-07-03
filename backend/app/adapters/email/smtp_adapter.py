from __future__ import annotations

import asyncio
import smtplib
import uuid
from email.message import EmailMessage

from app.adapters.email.interfaces import EmailSendResult
from app.core.exceptions import ProviderError


class SmtpEmailSender:
    def __init__(self, host: str, port: int, username: str | None, password: str | None) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password

    async def send(
        self, *, to_address: str, from_address: str, subject: str, body_text: str, body_html: str | None = None
    ) -> EmailSendResult:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = from_address
        message["To"] = to_address
        message_id = f"<{uuid.uuid4()}@leadforge>"
        message["Message-ID"] = message_id
        message.set_content(body_text)
        if body_html:
            message.add_alternative(body_html, subtype="html")

        try:
            await asyncio.to_thread(self._send_sync, message)
        except (smtplib.SMTPException, OSError) as exc:
            raise ProviderError(f"SMTP send failed: {exc}") from exc

        return EmailSendResult(provider_message_id=message_id, provider="smtp")

    def _send_sync(self, message: EmailMessage) -> None:
        with smtplib.SMTP(self._host, self._port, timeout=20) as client:
            client.starttls()
            if self._username and self._password:
                client.login(self._username, self._password)
            client.send_message(message)
