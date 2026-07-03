from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.lighthouse_report import LighthouseReport
from app.models.website_snapshot import Screenshot, WebsiteSnapshot


class WebsiteSnapshotRepository(Protocol):
    async def create(self, snapshot: WebsiteSnapshot, screenshots: list[Screenshot]) -> WebsiteSnapshot: ...
    async def get_by_audit_job(self, audit_job_id: uuid.UUID) -> WebsiteSnapshot | None: ...


class SqlAlchemyWebsiteSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, snapshot: WebsiteSnapshot, screenshots: list[Screenshot]) -> WebsiteSnapshot:
        self._session.add(snapshot)
        await self._session.flush()  # populate snapshot.id
        for shot in screenshots:
            shot.website_snapshot_id = snapshot.id
            self._session.add(shot)
        await self._session.flush()
        return snapshot

    async def get_by_audit_job(self, audit_job_id: uuid.UUID) -> WebsiteSnapshot | None:
        stmt = (
            select(WebsiteSnapshot)
            .where(WebsiteSnapshot.audit_job_id == audit_job_id)
            .options(selectinload(WebsiteSnapshot.screenshots))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


class LighthouseReportRepository(Protocol):
    async def create(self, report: LighthouseReport) -> LighthouseReport: ...
    async def get_by_audit_job(self, audit_job_id: uuid.UUID) -> LighthouseReport | None: ...


class SqlAlchemyLighthouseReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, report: LighthouseReport) -> LighthouseReport:
        self._session.add(report)
        await self._session.flush()
        return report

    async def get_by_audit_job(self, audit_job_id: uuid.UUID) -> LighthouseReport | None:
        stmt = select(LighthouseReport).where(LighthouseReport.audit_job_id == audit_job_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
