from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.core.di import get_business_repository
from app.core.exceptions import NotFoundError
from app.core.security import Role, TokenPayload, get_current_token, require_role
from app.models.business import BusinessStatus
from app.repositories.business_repository import BusinessRepository
from app.schemas.business import BusinessListResponse, BusinessOut, BusinessUpdate
from app.services.validation.validation_service import WebsiteValidationService

router = APIRouter(prefix="/businesses", tags=["businesses"])


class ManualBusinessCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=120)
    city: str = Field(min_length=1, max_length=120)
    country: str = Field(min_length=1, max_length=120)
    website_url: str | None = None
    phone: str | None = None
    address: str | None = None


@router.get("", response_model=BusinessListResponse)
async def list_businesses(
    city: str | None = None,
    category: str | None = None,
    status: BusinessStatus | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    token: TokenPayload = Depends(get_current_token),
    repo: BusinessRepository = Depends(get_business_repository),
):
    org_id = uuid.UUID(token.org) if token.org else None
    items, total = await repo.list_filtered(
        organization_id=org_id, city=city, category=category, status=status, page=page, page_size=page_size
    )
    return BusinessListResponse(
        items=[BusinessOut.model_validate(b) for b in items], total=total, page=page, page_size=page_size
    )


@router.get("/{business_id}", response_model=BusinessOut)
async def get_business(
    business_id: uuid.UUID,
    token: TokenPayload = Depends(get_current_token),
    repo: BusinessRepository = Depends(get_business_repository),
):
    business = await repo.get_by_id(business_id)
    if business is None:
        raise NotFoundError("Business not found.")
    return business


@router.patch("/{business_id}", response_model=BusinessOut)
async def update_business(
    business_id: uuid.UUID,
    payload: BusinessUpdate,
    token: TokenPayload = Depends(require_role(Role.OWNER, Role.ADMIN, Role.ANALYST)),
    repo: BusinessRepository = Depends(get_business_repository),
):
    """General edit — the main use case is adding a website_url you found
    yourself to a business that was discovered without one (common for OSM
    discoveries). If a website_url is newly added where none existed
    before, it's validated immediately (same check discovery itself runs)
    so the business becomes auditable right away rather than staying stuck
    in "discovered" status until the next audit attempt fails."""
    existing = await repo.get_by_id(business_id)
    if existing is None:
        raise NotFoundError("Business not found.")

    data = payload.model_dump(exclude_unset=True)
    had_no_website_before = not existing.website_url

    business = await repo.update(business_id, data)

    if had_no_website_before and business and business.website_url:
        validator = WebsiteValidationService()
        result = await validator.validate(business.website_url)
        if result.is_valid:
            update_fields: dict = {"status": BusinessStatus.VALIDATED}
            if result.final_url:
                update_fields["website_url"] = result.final_url
            business = await repo.update(business_id, update_fields)

    return business


@router.post("", response_model=BusinessOut, status_code=201)
async def create_business(
    payload: ManualBusinessCreate,
    token: TokenPayload = Depends(require_role(Role.OWNER, Role.ADMIN, Role.ANALYST)),
    repo: BusinessRepository = Depends(get_business_repository),
):
    org_id = uuid.UUID(token.org) if token.org else None
    business = await repo.upsert_discovered(
        organization_id=org_id,
        data={
            "name": payload.name,
            "category": payload.category,
            "city": payload.city,
            "country": payload.country,
            "website_url": payload.website_url,
            "phone": payload.phone,
            "address": payload.address,
            "google_place_id": None,
            "google_rating": None,
            "review_count": None,
            "latitude": None,
            "longitude": None,
            "discovery_provider": "manual",
        },
    )
    return business


@router.patch("/{business_id}/archive", response_model=BusinessOut)
async def archive_business(
    business_id: uuid.UUID,
    token: TokenPayload = Depends(require_role(Role.OWNER, Role.ADMIN, Role.ANALYST)),
    repo: BusinessRepository = Depends(get_business_repository),
):
    business = await repo.update_status(business_id, BusinessStatus.ARCHIVED)
    if business is None:
        raise NotFoundError("Business not found.")
    return business


@router.delete("/{business_id}", status_code=204)
async def delete_business(
    business_id: uuid.UUID,
    token: TokenPayload = Depends(require_role(Role.OWNER, Role.ADMIN, Role.ANALYST)),
    repo: BusinessRepository = Depends(get_business_repository),
):
    """Hard delete — removes the business and everything derived from it
    (audit jobs, screenshots, findings, lead scores, campaigns, outreach
    emails) via cascading foreign keys. Use `/archive` instead if you just
    want to hide a business without losing its audit history."""
    deleted = await repo.delete(business_id)
    if not deleted:
        raise NotFoundError("Business not found.")