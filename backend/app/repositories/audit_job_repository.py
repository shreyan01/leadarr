from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit_job import AuditJob, AuditStatus, JobEvent, JobEventStatus


class AuditJobRepository(Protocol):
    async def create(self, *, business_id: uuid.UUID, organization_id: uuid.UUID | None) -> AuditJob: ...
    async def get_by_id(self, audit_job_id: uuid.UUID, *, with_events: bool = False) -> AuditJob | None: ...
    async def mark_stage_started(self, audit_job_id: uuid.UUID, stage: str) -> None: ...
    async def mark_completed(self, audit_job_id: uuid.UUID) -> None: ...
    async def mark_failed(self, audit_job_id: uuid.UUID, *, stage: str, error_message: str) -> None: ...
    async def log_event(
        self, *, audit_job_id: uuid.UUID, stage: str, status: JobEventStatus,
        duration_ms: int | None = None, retries: int = 0, model_used: str | None = None,
        tokens_input: int | None = None, tokens_output: int | None = None,
        cost_usd: float | None = None, message: str | None = None,
    ) -> JobEvent: ...


class SqlAlchemyAuditJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, business_id: uuid.UUID, organization_id: uuid.UUID | None) -> AuditJob:
        job = AuditJob(
            business_id=business_id,
            organization_id=organization_id,
            status=AuditStatus.PENDING,
            started_at=datetime.now(timezone.utc),
        )
        self._session.add(job)
        await self._session.flush()
        return job

    async def get_by_id(self, audit_job_id: uuid.UUID, *, with_events: bool = False) -> AuditJob | None:
        stmt = select(AuditJob).where(AuditJob.id == audit_job_id)
        if with_events:
            stmt = stmt.options(selectinload(AuditJob.events))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_stage_started(self, audit_job_id: uuid.UUID, stage: str) -> None:
        job = await self.get_by_id(audit_job_id)
        if job is None:
            return
        job.status = AuditStatus.RUNNING
        job.current_stage = stage
        await self._session.flush()

    async def mark_completed(self, audit_job_id: uuid.UUID) -> None:
        job = await self.get_by_id(audit_job_id)
        if job is None:
            return
        job.status = AuditStatus.COMPLETED
        job.finished_at = datetime.now(timezone.utc)
        await self._session.flush()

    async def mark_failed(self, audit_job_id: uuid.UUID, *, stage: str, error_message: str) -> None:
        job = await self.get_by_id(audit_job_id)
        if job is None:
            return
        job.status = AuditStatus.FAILED
        job.failed_stage = stage
        job.error_message = error_message[:2000]
        job.finished_at = datetime.now(timezone.utc)
        await self._session.flush()

    async def log_event(
        self, *, audit_job_id: uuid.UUID, stage: str, status: JobEventStatus,
        duration_ms: int | None = None, retries: int = 0, model_used: str | None = None,
        tokens_input: int | None = None, tokens_output: int | None = None,
        cost_usd: float | None = None, message: str | None = None,
    ) -> JobEvent:
        event = JobEvent(
            audit_job_id=audit_job_id, stage=stage, status=status, duration_ms=duration_ms, retries=retries,
            model_used=model_used, tokens_input=tokens_input, tokens_output=tokens_output,
            cost_usd=cost_usd, message=message,
        )
        self._session.add(event)
        await self._session.flush()
        return event
