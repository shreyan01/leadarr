from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.campaign import Campaign, CampaignEvent, CampaignStage


class CampaignRepository(Protocol):
    async def get_or_create_for_business(
        self, *, business_id: uuid.UUID, organization_id: uuid.UUID | None, name: str
    ) -> Campaign: ...
    async def get_by_id(self, campaign_id: uuid.UUID, *, with_events: bool = False) -> Campaign | None: ...
    async def set_stage(self, campaign_id: uuid.UUID, stage: CampaignStage) -> Campaign | None: ...
    async def add_event(
        self, *, campaign_id: uuid.UUID, event_type: str, note: str | None, created_by: uuid.UUID | None
    ) -> CampaignEvent: ...
    async def set_follow_up(self, campaign_id: uuid.UUID, follow_up_at: datetime) -> Campaign | None: ...
    async def list_by_stage(
        self, *, organization_id: uuid.UUID | None, stage: CampaignStage | None = None
    ) -> list[Campaign]: ...


class SqlAlchemyCampaignRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_for_business(
        self, *, business_id: uuid.UUID, organization_id: uuid.UUID | None, name: str
    ) -> Campaign:
        existing = await self._session.execute(select(Campaign).where(Campaign.business_id == business_id))
        campaign = existing.scalar_one_or_none()
        if campaign is not None:
            return campaign

        campaign = Campaign(business_id=business_id, organization_id=organization_id, name=name)
        self._session.add(campaign)
        await self._session.flush()
        return campaign

    async def get_by_id(self, campaign_id: uuid.UUID, *, with_events: bool = False) -> Campaign | None:
        stmt = select(Campaign).where(Campaign.id == campaign_id)
        if with_events:
            stmt = stmt.options(selectinload(Campaign.events))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def set_stage(self, campaign_id: uuid.UUID, stage: CampaignStage) -> Campaign | None:
        campaign = await self.get_by_id(campaign_id)
        if campaign is None:
            return None
        campaign.stage = stage
        await self._session.flush()
        return campaign

    async def add_event(
        self, *, campaign_id: uuid.UUID, event_type: str, note: str | None, created_by: uuid.UUID | None
    ) -> CampaignEvent:
        event = CampaignEvent(
            campaign_id=campaign_id, event_type=event_type, note=note,
            occurred_at=datetime.now(timezone.utc), created_by=created_by,
        )
        self._session.add(event)
        await self._session.flush()
        return event

    async def set_follow_up(self, campaign_id: uuid.UUID, follow_up_at: datetime) -> Campaign | None:
        campaign = await self.get_by_id(campaign_id)
        if campaign is None:
            return None
        campaign.next_follow_up_at = follow_up_at
        await self._session.flush()
        return campaign

    async def list_by_stage(
        self, *, organization_id: uuid.UUID | None, stage: CampaignStage | None = None
    ) -> list[Campaign]:
        stmt = select(Campaign).where(Campaign.organization_id == organization_id)
        if stage:
            stmt = stmt.where(Campaign.stage == stage)
        stmt = stmt.order_by(Campaign.updated_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
