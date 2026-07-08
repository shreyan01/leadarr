from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.ai.interfaces import Message
from app.ai.registry import get_chat_provider
from app.core.config import Settings, get_settings
from app.core.di import (
    get_ai_report_repository,
    get_business_repository,
    get_campaign_repository,
    get_email_send_service,
    get_outreach_email_repository,
)
from app.core.exceptions import LeadForgeError, NotFoundError
from app.core.security import Role, TokenPayload, get_current_token, require_role
from app.models.audit_job import AuditJob, AuditStatus
from app.models.campaign import CampaignStage
from app.models.outreach_email import OutreachEmail
from app.repositories.ai_report_repository import AIReportRepository
from app.repositories.business_repository import BusinessRepository
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.outreach_email_repository import OutreachEmailRepository
from app.schemas.email import EmailDraftRequest, EmailSendRequest, EmailUpdateRequest, OutreachEmailOut
from app.services.outreach.email_parser import parse_email_response
from app.services.outreach.email_prompts import EmailInputs, build_email_prompt
from app.services.outreach.email_send_service import EmailSendService

router = APIRouter(tags=["outreach"])


async def _latest_report_for_business(business_id: uuid.UUID, report_repo: AIReportRepository):
    """AIReport is keyed by audit_job_id, not business_id directly — find
    the most recent completed audit job for this business and look up its
    report through the repository's own session."""
    session = getattr(report_repo, "_session", None)
    if session is None:
        return None

    result = await session.execute(
        select(AuditJob)
        .where(AuditJob.business_id == business_id, AuditJob.status == AuditStatus.COMPLETED)
        .order_by(AuditJob.finished_at.desc())
        .limit(1)
    )
    latest_job = result.scalar_one_or_none()
    if latest_job is None:
        return None
    return await report_repo.get_by_audit_job(latest_job.id)


@router.post("/businesses/{business_id}/emails", response_model=OutreachEmailOut, status_code=201)
async def draft_email(
    business_id: uuid.UUID,
    payload: EmailDraftRequest,
    token: TokenPayload = Depends(require_role(Role.OWNER, Role.ADMIN, Role.ANALYST)),
    business_repo: BusinessRepository = Depends(get_business_repository),
    report_repo: AIReportRepository = Depends(get_ai_report_repository),
    email_repo: OutreachEmailRepository = Depends(get_outreach_email_repository),
    campaign_repo: CampaignRepository = Depends(get_campaign_repository),
    settings: Settings = Depends(get_settings),
):
    """Generates a fresh outreach draft on demand (outside the automated
    pipeline), e.g. to try a different template for an already-audited lead."""
    business = await business_repo.get_by_id(business_id)
    if business is None:
        raise NotFoundError("Business not found.")

    report = await _latest_report_for_business(business_id, report_repo)
    if report is None:
        if business.website_url:
            raise LeadForgeError("No AI report found for this business yet — run an audit first.")
        # No website at all means no audit is even possible for this
        # business — the "you don't have a website yet" pitch is a
        # legitimate, often strong lead in its own right (see
        # Business.is_social_only_lead), so it shouldn't be permanently
        # blocked on a report that can never exist. Falls back to a
        # summary built from whatever contact info discovery actually found.
        contact_channels = [
            c
            for c in [
                "a Facebook page" if business.facebook_url else None,
                "an Instagram page" if business.instagram_url else None,
                "a phone number" if business.phone else None,
            ]
            if c
        ]
        channels_text = " and ".join(contact_channels) if contact_channels else "no online presence we could find"
        executive_summary = (
            f"{business.name} does not appear to have a website. They currently have {channels_text}."
        )
        top_improvements = [
            {
                "title": "Build a professional website",
                "detail": "No website was found for this business during discovery.",
                "category": "design",
            }
        ]
    else:
        executive_summary = report.executive_summary or ""
        top_improvements = (report.top_improvements or {}).get("items", [])

    email_inputs = EmailInputs(
        business_name=business.name,
        category=business.category,
        sender_agency_name=settings.APP_NAME,
        executive_summary=executive_summary,
        top_improvements=top_improvements,
        lead_score=None,
        priority=None,
        template_key=payload.template_key,
    )

    chat = get_chat_provider(settings)
    prompt = build_email_prompt(email_inputs)
    result = await chat.complete(
        [Message(role="user", content=prompt)], model=settings.DEFAULT_CHAT_MODEL, temperature=0.4, max_tokens=1200
    )
    parsed = parse_email_response(result.text)

    email = await email_repo.create(
        OutreachEmail(
            business_id=business_id,
            audit_job_id=None,
            template_key=payload.template_key,
            subject=parsed["subject"],
            body_text=parsed["body_text"],
            body_html=parsed["body_html"],
            provider="anthropic",
            model=result.model,
        )
    )

    campaign = await campaign_repo.get_or_create_for_business(
        business_id=business_id, organization_id=business.organization_id, name=business.name
    )
    await campaign_repo.set_stage(campaign.id, CampaignStage.EMAIL_DRAFTED)

    return email


@router.get("/businesses/{business_id}/emails", response_model=list[OutreachEmailOut])
async def list_emails(
    business_id: uuid.UUID,
    token: TokenPayload = Depends(get_current_token),
    email_repo: OutreachEmailRepository = Depends(get_outreach_email_repository),
):
    return await email_repo.list_by_business(business_id)


@router.patch("/emails/{email_id}", response_model=OutreachEmailOut)
async def update_email(
    email_id: uuid.UUID,
    payload: EmailUpdateRequest,
    token: TokenPayload = Depends(require_role(Role.OWNER, Role.ADMIN, Role.ANALYST)),
    email_repo: OutreachEmailRepository = Depends(get_outreach_email_repository),
):
    email = await email_repo.get_by_id(email_id)
    if email is None:
        raise NotFoundError("Outreach email not found.")
    if payload.subject is not None:
        email.subject = payload.subject
    if payload.body_text is not None:
        email.body_text = payload.body_text
    if payload.body_html is not None:
        email.body_html = payload.body_html
    return await email_repo.update(email)


@router.post("/emails/{email_id}/send", response_model=OutreachEmailOut)
async def send_email(
    email_id: uuid.UUID,
    payload: EmailSendRequest,
    token: TokenPayload = Depends(require_role(Role.OWNER, Role.ADMIN, Role.ANALYST)),
    send_service: EmailSendService = Depends(get_email_send_service),
):
    org_id = uuid.UUID(token.org) if token.org else None
    return await send_service.send(email_id=email_id, to_address=payload.to_address, organization_id=org_id)