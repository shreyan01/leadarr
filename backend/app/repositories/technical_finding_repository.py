from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.technical_finding import TechnicalFinding


class TechnicalFindingRepository(Protocol):
    async def create(self, finding: TechnicalFinding) -> TechnicalFinding: ...
    async def get_by_audit_job(self, audit_job_id: uuid.UUID) -> TechnicalFinding | None: ...


class SqlAlchemyTechnicalFindingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, finding: TechnicalFinding) -> TechnicalFinding:
        self._session.add(finding)
        await self._session.flush()
        return finding

    async def get_by_audit_job(self, audit_job_id: uuid.UUID) -> TechnicalFinding | None:
        result = await self._session.execute(
            select(TechnicalFinding).where(TechnicalFinding.audit_job_id == audit_job_id)
        )
        return result.scalar_one_or_none()