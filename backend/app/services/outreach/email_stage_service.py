from __future__ import annotations

import uuid

from app.ai.interfaces import ChatProvider, Message
from app.core.logging import get_logger
from app.models.audit_job import JobEventStatus
from app.models.campaign import CampaignStage
from app.models.outreach_email import OutreachEmail
from app.repositories.audit_job_repository import AuditJobRepository
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.outreach_email_repository import OutreachEmailRepository
from app.services.outreach.email_parser import parse_email_response
from app.services.outreach.email_prompts import EmailInputs, build_email_prompt
from app.utils.stage_timer import stage_timer

logger = get_logger(__name__)

STAGE_NAME = "outreach_draft"


class EmailDraftStageService:
    def __init__(
        self,
        chat_provider: ChatProvider,
        email_repo: OutreachEmailRepository,
        campaign_repo: CampaignRepository,
        audit_job_repo: AuditJobRepository,
        model: str,
    ) -> None:
        self._chat = chat_provider
        self._emails = email_repo
        self._campaigns = campaign_repo
        self._audit_jobs = audit_job_repo
        self._model = model

    async def run(
        self,
        *,
        audit_job_id: uuid.UUID,
        business_id: uuid.UUID,
        organization_id: uuid.UUID | None,
        business_name: str,
        report_inputs: EmailInputs,
    ) -> OutreachEmail:
        await self._audit_jobs.mark_stage_started(audit_job_id, STAGE_NAME)

        with stage_timer() as elapsed_ms:
            try:
                prompt = build_email_prompt(report_inputs)
                result = await self._chat.complete(
                    [Message(role="user", content=prompt)], model=self._model, temperature=0.4, max_tokens=1200
                )
                parsed = parse_email_response(result.text)
            except Exception as exc:
                await self._audit_jobs.log_event(
                    audit_job_id=audit_job_id, stage=STAGE_NAME, status=JobEventStatus.FAILED,
                    duration_ms=elapsed_ms(), message=str(exc)[:1000],
                )
                raise

            email = OutreachEmail(
                business_id=business_id,
                audit_job_id=audit_job_id,
                template_key=report_inputs.template_key,
                subject=parsed["subject"],
                body_text=parsed["body_text"],
                body_html=parsed["body_html"],
                provider=getattr(self._chat, "provider_name", "openai-compatible"),
                model=result.model,
            )
            await self._emails.create(email)

            campaign = await self._campaigns.get_or_create_for_business(
                business_id=business_id, organization_id=organization_id, name=business_name
            )
            await self._campaigns.set_stage(campaign.id, CampaignStage.EMAIL_DRAFTED)
            await self._campaigns.add_event(
                campaign_id=campaign.id, event_type="email_drafted", note=f"Draft: {parsed['subject']}", created_by=None
            )

            await self._audit_jobs.log_event(
                audit_job_id=audit_job_id, stage=STAGE_NAME, status=JobEventStatus.SUCCEEDED,
                duration_ms=elapsed_ms(), model_used=result.model,
                tokens_input=result.input_tokens, tokens_output=result.output_tokens,
            )

        logger.info("email_draft_stage_completed", audit_job_id=str(audit_job_id), business_id=str(business_id))
        return email
