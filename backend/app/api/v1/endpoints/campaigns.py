from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.core.di import get_campaign_repository
from app.core.exceptions import NotFoundError
from app.core.security import Role, TokenPayload, get_current_token, require_role
from app.models.campaign import CampaignStage
from app.repositories.campaign_repository import CampaignRepository
from app.schemas.campaign import (
    CampaignFollowUpUpdate,
    CampaignNoteCreate,
    CampaignOut,
    CampaignStageUpdate,
)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=list[CampaignOut])
async def list_campaigns(
    stage: CampaignStage | None = None,
    token: TokenPayload = Depends(get_current_token),
    repo: CampaignRepository = Depends(get_campaign_repository),
):
    """Kanban-style listing — group client-side by `stage`."""
    org_id = uuid.UUID(token.org) if token.org else None
    return await repo.list_by_stage(organization_id=org_id, stage=stage)


@router.patch("/{campaign_id}/stage", response_model=CampaignOut)
async def update_campaign_stage(
    campaign_id: uuid.UUID,
    payload: CampaignStageUpdate,
    token: TokenPayload = Depends(require_role(Role.OWNER, Role.ADMIN, Role.ANALYST)),
    repo: CampaignRepository = Depends(get_campaign_repository),
):
    campaign = await repo.set_stage(campaign_id, payload.stage)
    if campaign is None:
        raise NotFoundError("Campaign not found.")
    await repo.add_event(
        campaign_id=campaign_id, event_type="stage_changed", note=f"Moved to {payload.stage.value}", created_by=None
    )
    return campaign


@router.post("/{campaign_id}/notes", response_model=CampaignOut)
async def add_campaign_note(
    campaign_id: uuid.UUID,
    payload: CampaignNoteCreate,
    token: TokenPayload = Depends(require_role(Role.OWNER, Role.ADMIN, Role.ANALYST)),
    repo: CampaignRepository = Depends(get_campaign_repository),
):
    user_id = uuid.UUID(token.sub)
    campaign = await repo.get_by_id(campaign_id)
    if campaign is None:
        raise NotFoundError("Campaign not found.")
    await repo.add_event(campaign_id=campaign_id, event_type="note", note=payload.note, created_by=user_id)
    return await repo.get_by_id(campaign_id, with_events=True)


@router.patch("/{campaign_id}/follow-up", response_model=CampaignOut)
async def set_follow_up(
    campaign_id: uuid.UUID,
    payload: CampaignFollowUpUpdate,
    token: TokenPayload = Depends(require_role(Role.OWNER, Role.ADMIN, Role.ANALYST)),
    repo: CampaignRepository = Depends(get_campaign_repository),
):
    campaign = await repo.set_follow_up(campaign_id, payload.follow_up_at)
    if campaign is None:
        raise NotFoundError("Campaign not found.")
    return campaign
