from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.models.audit_job import JobEventStatus
from app.models.business import BusinessStatus
from app.models.lead_score import LeadScore
from app.models.lead_score import LeadPriority as LeadScoreModelPriority
from app.repositories.audit_job_repository import AuditJobRepository
from app.repositories.business_repository import BusinessRepository
from app.repositories.lead_score_repository import LeadScoreRepository
from app.services.scoring.lead_scoring_engine import ScoreInputs, compute_lead_score
from app.utils.stage_timer import stage_timer

logger = get_logger(__name__)

STAGE_NAME = "scoring"

_COMPONENT_FIELD_MAP = {
    "performance": "performance_component",
    "security": "security_component",
    "accessibility": "accessibility_component",
    "seo": "seo_component",
    "design": "design_component",
    "business_rating": "business_rating_component",
    "review_count": "review_count_component",
    "website_age": "website_age_component",
    "technology": "technology_component",
}


class ScoringStageService:
    def __init__(
        self, score_repo: LeadScoreRepository, business_repo: BusinessRepository, audit_job_repo: AuditJobRepository
    ) -> None:
        self._scores = score_repo
        self._businesses = business_repo
        self._audit_jobs = audit_job_repo

    async def run(self, *, audit_job_id: uuid.UUID, business_id: uuid.UUID, inputs: ScoreInputs) -> LeadScore:
        await self._audit_jobs.mark_stage_started(audit_job_id, STAGE_NAME)

        with stage_timer() as elapsed_ms:
            try:
                result = compute_lead_score(inputs)
            except Exception as exc:
                await self._audit_jobs.log_event(
                    audit_job_id=audit_job_id, stage=STAGE_NAME, status=JobEventStatus.FAILED,
                    duration_ms=elapsed_ms(), message=str(exc)[:1000],
                )
                raise

            score_row = LeadScore(
                business_id=business_id,
                audit_job_id=audit_job_id,
                overall_score=result.overall_score,
                priority=LeadScoreModelPriority(result.priority.value),
                scored_at=datetime.now(timezone.utc),
                **{
                    field_name: result.components.get(key)
                    for key, field_name in _COMPONENT_FIELD_MAP.items()
                },
            )
            await self._scores.create(score_row)
            await self._businesses.update_status(business_id, BusinessStatus.AUDITED)

            await self._audit_jobs.log_event(
                audit_job_id=audit_job_id, stage=STAGE_NAME, status=JobEventStatus.SUCCEEDED, duration_ms=elapsed_ms(),
            )

        logger.info(
            "scoring_stage_completed", audit_job_id=str(audit_job_id),
            overall_score=result.overall_score, priority=result.priority.value,
        )
        return score_row
