from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenPayload, get_current_token
from app.db.session import get_db
from app.models.audit_job import AuditJob, AuditStatus, JobEvent
from app.models.lead_score import LeadScore

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/stats")
async def get_stats(
    token: TokenPayload = Depends(get_current_token),
    session: AsyncSession = Depends(get_db),
):
    org_id = uuid.UUID(token.org) if token.org else None

    total_jobs = (
        await session.execute(
            select(func.count()).select_from(AuditJob).where(AuditJob.organization_id == org_id)
        )
    ).scalar_one()
    failed_jobs = (
        await session.execute(
            select(func.count())
            .select_from(AuditJob)
            .where(AuditJob.organization_id == org_id, AuditJob.status == AuditStatus.FAILED)
        )
    ).scalar_one()
    failure_rate = round(failed_jobs / total_jobs, 4) if total_jobs else 0.0

    avg_duration_seconds = (
        await session.execute(
            select(func.avg(func.extract("epoch", AuditJob.finished_at - AuditJob.started_at)))
            .where(
                AuditJob.organization_id == org_id,
                AuditJob.status == AuditStatus.COMPLETED,
                AuditJob.started_at.isnot(None),
                AuditJob.finished_at.isnot(None),
            )
        )
    ).scalar_one()

    avg_lead_score = (
        await session.execute(
            select(func.avg(LeadScore.overall_score)).join(AuditJob, AuditJob.id == LeadScore.audit_job_id).where(
                AuditJob.organization_id == org_id
            )
        )
    ).scalar_one()

    ai_usage = (
        await session.execute(
            select(
                func.sum(JobEvent.tokens_input),
                func.sum(JobEvent.tokens_output),
                func.sum(JobEvent.cost_usd),
            )
            .join(AuditJob, AuditJob.id == JobEvent.audit_job_id)
            .where(AuditJob.organization_id == org_id)
        )
    ).one()

    return {
        "total_audit_jobs": total_jobs,
        "failed_audit_jobs": failed_jobs,
        "failure_rate": failure_rate,
        "avg_audit_duration_seconds": round(avg_duration_seconds, 1) if avg_duration_seconds else None,
        "avg_lead_score": round(float(avg_lead_score), 2) if avg_lead_score else None,
        "ai_usage": {
            "total_input_tokens": int(ai_usage[0] or 0),
            "total_output_tokens": int(ai_usage[1] or 0),
            "total_cost_usd": float(ai_usage[2]) if ai_usage[2] else 0.0,
        },
    }
