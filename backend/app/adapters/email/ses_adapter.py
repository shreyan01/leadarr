from __future__ import annotations

import asyncio

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.adapters.email.interfaces import EmailSendResult
from app.core.exceptions import ProviderError


class SesEmailSender:
    def __init__(self, region: str) -> None:
        self._client = boto3.client("ses", region_name=region)

    async def send(
        self, *, to_address: str, from_address: str, subject: str, body_text: str, body_html: str | None = None
    ) -> EmailSendResult:
        try:
            response = await asyncio.to_thread(
                self._send_sync, to_address, from_address, subject, body_text, body_html
            )
        except (BotoCoreError, ClientError) as exc:
            raise ProviderError(f"AWS SES send failed: {exc}") from exc

        return EmailSendResult(provider_message_id=response["MessageId"], provider="ses")

    def _send_sync(
        self, to_address: str, from_address: str, subject: str, body_text: str, body_html: str | None
    ) -> dict:
        body: dict = {"Text": {"Data": body_text}}
        if body_html:
            body["Html"] = {"Data": body_html}
        return self._client.send_email(
            Source=from_address,
            Destination={"ToAddresses": [to_address]},
            Message={"Subject": {"Data": subject}, "Body": body},
        )
