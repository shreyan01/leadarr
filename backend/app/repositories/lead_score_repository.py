from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import Business
from app.models.lead_score import LeadScore


class LeadScoreRepository(Protocol):
    async def create(self, score: LeadScore) -> LeadScore: ...
    async def get_latest_for_business(self, business_id: uuid.UUID) -> LeadScore | None: ...
    async def list_ranked(
        self, *, organization_id: uuid.UUID | None, priority: str | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[LeadScore], int]: ...


class SqlAlchemyLeadScoreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, score: LeadScore) -> LeadScore:
        self._session.add(score)
        await self._session.flush()
        return score

    async def get_latest_for_business(self, business_id: uuid.UUID) -> LeadScore | None:
        stmt = (
            select(LeadScore)
            .where(LeadScore.business_id == business_id)
            .order_by(LeadScore.scored_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_ranked(
        self, *, organization_id: uuid.UUID | None, priority: str | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[LeadScore], int]:
        # Ranks each business by its most recent score (one row per business,
        # not one row per historical score).
        latest_ids_subq = (
            select(LeadScore.business_id, func.max(LeadScore.scored_at).label("max_scored_at"))
            .group_by(LeadScore.business_id)
            .subquery()
        )
        stmt = (
            select(LeadScore)
            .join(
                latest_ids_subq,
                (LeadScore.business_id == latest_ids_subq.c.business_id)
                & (LeadScore.scored_at == latest_ids_subq.c.max_scored_at),
            )
            .join(Business, Business.id == LeadScore.business_id)
            .where(Business.organization_id == organization_id)
        )
        count_stmt = (
            select(func.count())
            .select_from(LeadScore)
            .join(
                latest_ids_subq,
                (LeadScore.business_id == latest_ids_subq.c.business_id)
                & (LeadScore.scored_at == latest_ids_subq.c.max_scored_at),
            )
            .join(Business, Business.id == LeadScore.business_id)
            .where(Business.organization_id == organization_id)
        )

        if priority:
            stmt = stmt.where(LeadScore.priority == priority)
            count_stmt = count_stmt.where(LeadScore.priority == priority)

        stmt = stmt.order_by(LeadScore.overall_score.desc()).offset((page - 1) * page_size).limit(page_size)

        total = (await self._session.execute(count_stmt)).scalar_one()
        rows = (await self._session.execute(stmt)).scalars().all()
        return list(rows), total
