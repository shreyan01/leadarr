from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accessibility_finding import AccessibilityFinding
from app.models.security_finding import SecurityFinding
from app.models.vision_analysis import VisionAnalysis


class SecurityFindingRepository(Protocol):
    async def create(self, finding: SecurityFinding) -> SecurityFinding: ...
    async def get_by_audit_job(self, audit_job_id: uuid.UUID) -> SecurityFinding | None: ...


class SqlAlchemySecurityFindingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, finding: SecurityFinding) -> SecurityFinding:
        self._session.add(finding)
        await self._session.flush()
        return finding

    async def get_by_audit_job(self, audit_job_id: uuid.UUID) -> SecurityFinding | None:
        result = await self._session.execute(
            select(SecurityFinding).where(SecurityFinding.audit_job_id == audit_job_id)
        )
        return result.scalar_one_or_none()


class AccessibilityFindingRepository(Protocol):
    async def create(self, finding: AccessibilityFinding) -> AccessibilityFinding: ...
    async def get_by_audit_job(self, audit_job_id: uuid.UUID) -> AccessibilityFinding | None: ...


class SqlAlchemyAccessibilityFindingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, finding: AccessibilityFinding) -> AccessibilityFinding:
        self._session.add(finding)
        await self._session.flush()
        return finding

    async def get_by_audit_job(self, audit_job_id: uuid.UUID) -> AccessibilityFinding | None:
        result = await self._session.execute(
            select(AccessibilityFinding).where(AccessibilityFinding.audit_job_id == audit_job_id)
        )
        return result.scalar_one_or_none()


class VisionAnalysisRepository(Protocol):
    async def create(self, analysis: VisionAnalysis) -> VisionAnalysis: ...
    async def list_by_audit_job(self, audit_job_id: uuid.UUID) -> list[VisionAnalysis]: ...


class SqlAlchemyVisionAnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, analysis: VisionAnalysis) -> VisionAnalysis:
        self._session.add(analysis)
        await self._session.flush()
        return analysis

    async def list_by_audit_job(self, audit_job_id: uuid.UUID) -> list[VisionAnalysis]:
        result = await self._session.execute(
            select(VisionAnalysis).where(VisionAnalysis.audit_job_id == audit_job_id)
        )
        return list(result.scalars().all())
