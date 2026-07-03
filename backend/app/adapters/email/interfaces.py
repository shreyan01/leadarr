"""Provider-agnostic email-sending contract. ``services/outreach`` depends
only on this Protocol; adding a new provider (Mailgun, Postmark, ...) means
one adapter class + one registry entry."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class EmailSendResult:
    provider_message_id: str
    provider: str


class EmailSender(Protocol):
    async def send(
        self, *, to_address: str, from_address: str, subject: str, body_text: str, body_html: str | None = None
    ) -> EmailSendResult: ...
