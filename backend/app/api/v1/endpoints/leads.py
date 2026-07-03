from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from app.core.di import get_lead_score_repository
from app.core.exceptions import NotFoundError
from app.core.security import TokenPayload, get_current_token
from app.models.lead_score import LeadPriority
from app.repositories.lead_score_repository import LeadScoreRepository
from app.schemas.lead import LeadListResponse, LeadScoreOut

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("", response_model=LeadListResponse)
async def list_leads(
    priority: LeadPriority | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    token: TokenPayload = Depends(get_current_token),
    repo: LeadScoreRepository = Depends(get_lead_score_repository),
):
    org_id = uuid.UUID(token.org) if token.org else None
    items, total = await repo.list_ranked(
        organization_id=org_id, priority=priority.value if priority else None, page=page, page_size=page_size
    )
    return LeadListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{business_id}/score", response_model=LeadScoreOut)
async def get_lead_score(
    business_id: uuid.UUID,
    token: TokenPayload = Depends(get_current_token),
    repo: LeadScoreRepository = Depends(get_lead_score_repository),
):
    score = await repo.get_latest_for_business(business_id)
    if score is None:
        raise NotFoundError("No lead score found for this business.")
    return score
