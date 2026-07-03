from __future__ import annotations

import uuid

from app.adapters.email.interfaces import EmailSender
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.campaign import CampaignStage
from app.models.outreach_email import EmailStatus, OutreachEmail
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.outreach_email_repository import OutreachEmailRepository

logger = get_logger(__name__)


class EmailSendService:
    def __init__(
        self,
        sender: EmailSender,
        email_repo: OutreachEmailRepository,
        campaign_repo: CampaignRepository,
        from_address: str,
    ) -> None:
        self._sender = sender
        self._emails = email_repo
        self._campaigns = campaign_repo
        self._from_address = from_address

    async def send(self, *, email_id: uuid.UUID, to_address: str, organization_id: uuid.UUID | None) -> OutreachEmail:
        email = await self._emails.get_by_id(email_id)
        if email is None:
            raise NotFoundError("Outreach email not found.")
        if email.status == EmailStatus.SENT:
            raise ValidationError("This email has already been sent.")

        result = await self._sender.send(
            to_address=to_address, from_address=self._from_address,
            subject=email.subject, body_text=email.body_text, body_html=email.body_html,
        )
        email.status = EmailStatus.SENT
        await self._emails.update(email)

        campaign = await self._campaigns.get_or_create_for_business(
            business_id=email.business_id, organization_id=organization_id, name=email.subject
        )
        await self._campaigns.set_stage(campaign.id, CampaignStage.SENT)
        await self._campaigns.add_event(
            campaign_id=campaign.id, event_type="sent",
            note=f"Sent via {result.provider} (id: {result.provider_message_id})", created_by=None,
        )

        logger.info("outreach_email_sent", email_id=str(email_id), provider=result.provider)
        return email
