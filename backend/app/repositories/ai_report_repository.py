from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_report import AIReport


class AIReportRepository(Protocol):
    async def create(self, report: AIReport) -> AIReport: ...
    async def get_by_audit_job(self, audit_job_id: uuid.UUID) -> AIReport | None: ...


class SqlAlchemyAIReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, report: AIReport) -> AIReport:
        self._session.add(report)
        await self._session.flush()
        return report

    async def get_by_audit_job(self, audit_job_id: uuid.UUID) -> AIReport | None:
        result = await self._session.execute(select(AIReport).where(AIReport.audit_job_id == audit_job_id))
        return result.scalar_one_or_none()
