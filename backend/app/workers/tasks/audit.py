from __future__ import annotations

import asyncio
import uuid

from celery import chain, shared_task

from app.adapters.lighthouse_cli import LighthouseCliAdapter
from app.ai.registry import get_chat_provider, get_vision_provider
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.campaign import CampaignStage
from app.repositories.ai_report_repository import SqlAlchemyAIReportRepository
from app.repositories.audit_artifacts_repository import (
    SqlAlchemyLighthouseReportRepository,
    SqlAlchemyWebsiteSnapshotRepository,
)
from app.repositories.audit_job_repository import SqlAlchemyAuditJobRepository
from app.repositories.business_repository import SqlAlchemyBusinessRepository
from app.repositories.campaign_repository import SqlAlchemyCampaignRepository
from app.repositories.finding_repository import (
    SqlAlchemyAccessibilityFindingRepository,
    SqlAlchemySecurityFindingRepository,
    SqlAlchemyVisionAnalysisRepository,
)
from app.repositories.lead_score_repository import SqlAlchemyLeadScoreRepository
from app.repositories.outreach_email_repository import SqlAlchemyOutreachEmailRepository
from app.repositories.technical_finding_repository import SqlAlchemyTechnicalFindingRepository
from app.services.accessibility.accessibility_stage_service import AccessibilityStageService
from app.services.lighthouse.lighthouse_stage_service import LighthouseStageService
from app.services.outreach.email_prompts import EmailInputs
from app.services.outreach.email_stage_service import EmailDraftStageService
from app.services.outreach.email_templates import DEFAULT_TEMPLATE_KEY
from app.services.reporting.report_prompts import ReportInputs
from app.services.reporting.report_stage_service import ReportStageService
from app.services.technical.technical_stage_service import TechnicalAuditStageService
from app.services.scoring.lead_scoring_engine import ScoreInputs
from app.services.scoring.scoring_stage_service import ScoringStageService
from app.services.security_audit.security_audit_service import SecurityAuditStageService
from app.services.vision.vision_stage_service import VisionStageService
from app.utils.storage import get_storage_backend
from app.workers.async_utils import run_worker_task
from app.workers.celery_app import celery_app  # noqa: F401
from app.workers.tasks.crawl import run_crawl

logger = get_logger(__name__)


@shared_task(name="app.workers.tasks.audit.run_lighthouse", bind=True, max_retries=2, default_retry_delay=30)
def run_lighthouse(self, previous_result: dict) -> dict:
    return run_worker_task(_run_lighthouse_async(previous_result))


async def _run_lighthouse_async(previous_result: dict) -> dict:
    settings = get_settings()
    audit_job_id = uuid.UUID(previous_result["audit_job_id"])
    business_id = uuid.UUID(previous_result["business_id"])
    url = previous_result["final_url"]

    async with AsyncSessionLocal() as session:
        service = LighthouseStageService(
            cli=LighthouseCliAdapter(settings.LIGHTHOUSE_CLI_PATH),
            storage=get_storage_backend(settings),
            report_repo=SqlAlchemyLighthouseReportRepository(session),
            audit_job_repo=SqlAlchemyAuditJobRepository(session),
        )
        try:
            report = await service.run(audit_job_id=audit_job_id, business_id=business_id, url=url)
            await session.commit()
            return {
                "audit_job_id": str(audit_job_id),
                "business_id": str(business_id),
                "performance_score": report.performance_score,
                "accessibility_score": report.accessibility_score,
                "seo_score": report.seo_score,
                "best_practices_score": report.best_practices_score,
            }
        except Exception as exc:
            # LighthouseStageService.run() already logged a FAILED job_event
            # with the real error before re-raising — that's still visible
            # on the audit detail page per-stage. We just don't let it take
            # the rest of the audit down with it: real browser automation
            # (unlike every other stage, which is plain HTTP/static analysis)
            # is inherently the most fragile link here, and Lighthouse's own
            # numbers being unavailable doesn't block anything downstream.
            logger.warning(
                "lighthouse_failed_continuing_pipeline", audit_job_id=str(audit_job_id), error=str(exc)[:500]
            )
            await session.commit()
            return {
                "audit_job_id": str(audit_job_id),
                "business_id": str(business_id),
                "performance_score": None,
                "accessibility_score": None,
                "seo_score": None,
                "best_practices_score": None,
            }


@shared_task(name="app.workers.tasks.audit.run_accessibility", bind=True, max_retries=2, default_retry_delay=30)
def run_accessibility(self, previous_result: dict) -> dict:
    try:
        return run_worker_task(_run_accessibility_async(previous_result))
    except Exception as exc:  # noqa: BLE001
        logger.error("accessibility_task_failed", previous_result=previous_result, error=str(exc))
        raise self.retry(exc=exc) from exc


async def _run_accessibility_async(previous_result: dict) -> dict:
    settings = get_settings()
    audit_job_id = uuid.UUID(previous_result["audit_job_id"])

    async with AsyncSessionLocal() as session:
        snapshot = await SqlAlchemyWebsiteSnapshotRepository(session).get_by_audit_job(audit_job_id)
        if snapshot is None:
            raise RuntimeError(f"No website snapshot found for audit job {audit_job_id}; crawl stage may have failed.")

        service = AccessibilityStageService(
            storage=get_storage_backend(settings),
            finding_repo=SqlAlchemyAccessibilityFindingRepository(session),
            audit_job_repo=SqlAlchemyAuditJobRepository(session),
        )
        finding = await service.run(audit_job_id=audit_job_id, snapshot=snapshot)
        await session.commit()
        return {**previous_result, "accessibility_static_score": finding.accessibility_score}


@shared_task(name="app.workers.tasks.audit.run_security_audit", bind=True, max_retries=2, default_retry_delay=30)
def run_security_audit(self, previous_result: dict) -> dict:
    try:
        return run_worker_task(_run_security_audit_async(previous_result))
    except Exception as exc:  # noqa: BLE001
        logger.error("security_audit_task_failed", previous_result=previous_result, error=str(exc))
        raise self.retry(exc=exc) from exc


async def _run_security_audit_async(previous_result: dict) -> dict:
    audit_job_id = uuid.UUID(previous_result["audit_job_id"])

    async with AsyncSessionLocal() as session:
        snapshot = await SqlAlchemyWebsiteSnapshotRepository(session).get_by_audit_job(audit_job_id)
        if snapshot is None:
            raise RuntimeError(f"No website snapshot found for audit job {audit_job_id}; crawl stage may have failed.")

        finding_repo = SqlAlchemySecurityFindingRepository(session)
        audit_job_repo = SqlAlchemyAuditJobRepository(session)
        service = SecurityAuditStageService(finding_repo, audit_job_repo)
        finding = await service.run(audit_job_id=audit_job_id, snapshot=snapshot)
        await session.commit()
        return {**previous_result, "hygiene_score": finding.hygiene_score}


@shared_task(name="app.workers.tasks.audit.run_technical_audit", bind=True, max_retries=2, default_retry_delay=30)
def run_technical_audit(self, previous_result: dict) -> dict:
    try:
        return run_worker_task(_run_technical_audit_async(previous_result))
    except Exception as exc:  # noqa: BLE001
        logger.error("technical_audit_task_failed", previous_result=previous_result, error=str(exc))
        raise self.retry(exc=exc) from exc


async def _run_technical_audit_async(previous_result: dict) -> dict:
    settings = get_settings()
    audit_job_id = uuid.UUID(previous_result["audit_job_id"])

    async with AsyncSessionLocal() as session:
        snapshot = await SqlAlchemyWebsiteSnapshotRepository(session).get_by_audit_job(audit_job_id)
        if snapshot is None:
            raise RuntimeError(f"No website snapshot found for audit job {audit_job_id}; crawl stage may have failed.")

        finding_repo = SqlAlchemyTechnicalFindingRepository(session)
        audit_job_repo = SqlAlchemyAuditJobRepository(session)
        service = TechnicalAuditStageService(get_storage_backend(settings), finding_repo, audit_job_repo)
        finding = await service.run(audit_job_id=audit_job_id, snapshot=snapshot)
        await session.commit()
        return {**previous_result, "technical_score": finding.technical_score}


@shared_task(name="app.workers.tasks.audit.run_vision", bind=True, max_retries=2, default_retry_delay=30)
def run_vision(self, previous_result: dict) -> dict:
    try:
        return run_worker_task(_run_vision_async(previous_result))
    except Exception as exc:  # noqa: BLE001
        logger.error("vision_task_failed", previous_result=previous_result, error=str(exc))
        raise self.retry(exc=exc) from exc


async def _run_vision_async(previous_result: dict) -> dict:
    settings = get_settings()
    audit_job_id = uuid.UUID(previous_result["audit_job_id"])
    business_id = uuid.UUID(previous_result["business_id"])

    async with AsyncSessionLocal() as session:
        snapshot = await SqlAlchemyWebsiteSnapshotRepository(session).get_by_audit_job(audit_job_id)
        if snapshot is None:
            raise RuntimeError(f"No website snapshot found for audit job {audit_job_id}; crawl stage may have failed.")

        business = await SqlAlchemyBusinessRepository(session).get_by_id(business_id)
        business_name = business.name if business else "this business"

        audit_job_repo = SqlAlchemyAuditJobRepository(session)
        service = VisionStageService(
            vision_provider=get_vision_provider(settings),
            storage=get_storage_backend(settings),
            analysis_repo=SqlAlchemyVisionAnalysisRepository(session),
            audit_job_repo=audit_job_repo,
            model=settings.DEFAULT_VISION_MODEL,
        )
        analyses = await service.run(audit_job_id=audit_job_id, business_name=business_name, snapshot=snapshot)
        await session.commit()
        design_scores = [a.overall_score for a in analyses if a.overall_score is not None]
        design_score = round(sum(design_scores) / len(design_scores)) if design_scores else None
        return {**previous_result, "design_score": design_score}


@shared_task(name="app.workers.tasks.audit.run_scoring", bind=True, max_retries=2, default_retry_delay=30)
def run_scoring(self, previous_result: dict) -> dict:
    try:
        return run_worker_task(_run_scoring_async(previous_result))
    except Exception as exc:  # noqa: BLE001
        logger.error("scoring_task_failed", previous_result=previous_result, error=str(exc))
        raise self.retry(exc=exc) from exc


async def _run_scoring_async(previous_result: dict) -> dict:
    audit_job_id = uuid.UUID(previous_result["audit_job_id"])
    business_id = uuid.UUID(previous_result["business_id"])

    async with AsyncSessionLocal() as session:
        business_repo = SqlAlchemyBusinessRepository(session)
        business = await business_repo.get_by_id(business_id)
        security = await SqlAlchemySecurityFindingRepository(session).get_by_audit_job(audit_job_id)
        accessibility = await SqlAlchemyAccessibilityFindingRepository(session).get_by_audit_job(audit_job_id)

        inputs = ScoreInputs(
            performance_score=previous_result.get("performance_score"),
            seo_score=previous_result.get("seo_score"),
            accessibility_score=accessibility.accessibility_score if accessibility else None,
            security_hygiene_score=security.hygiene_score if security else None,
            design_score=previous_result.get("design_score"),
            google_rating=float(business.google_rating) if business and business.google_rating else None,
            review_count=business.review_count if business else None,
            website_age_years=None,  # not collected — domain-age lookup is a Phase 9+ enhancement
            outdated_technology=False,  # tech fingerprinting isn't persisted yet; see security_audit_service note
        )

        audit_job_repo = SqlAlchemyAuditJobRepository(session)
        service = ScoringStageService(SqlAlchemyLeadScoreRepository(session), business_repo, audit_job_repo)
        score = await service.run(audit_job_id=audit_job_id, business_id=business_id, inputs=inputs)

        if business is not None:
            campaign_repo = SqlAlchemyCampaignRepository(session)
            campaign = await campaign_repo.get_or_create_for_business(
                business_id=business_id, organization_id=business.organization_id, name=business.name
            )
            await campaign_repo.set_stage(campaign.id, CampaignStage.AUDITED)

        await session.commit()
        return {**previous_result, "lead_score": float(score.overall_score), "priority": score.priority.value}


@shared_task(name="app.workers.tasks.audit.run_reporting", bind=True, max_retries=2, default_retry_delay=30)
def run_reporting(self, previous_result: dict) -> dict:
    try:
        return run_worker_task(_run_reporting_async(previous_result))
    except Exception as exc:  # noqa: BLE001
        logger.error("reporting_task_failed", previous_result=previous_result, error=str(exc))
        raise self.retry(exc=exc) from exc


async def _run_reporting_async(previous_result: dict) -> dict:
    settings = get_settings()
    audit_job_id = uuid.UUID(previous_result["audit_job_id"])
    business_id = uuid.UUID(previous_result["business_id"])

    async with AsyncSessionLocal() as session:
        business = await SqlAlchemyBusinessRepository(session).get_by_id(business_id)
        if business is None:
            raise RuntimeError(f"Business {business_id} not found when generating report.")

        lighthouse = await SqlAlchemyLighthouseReportRepository(session).get_by_audit_job(audit_job_id)
        security = await SqlAlchemySecurityFindingRepository(session).get_by_audit_job(audit_job_id)
        accessibility = await SqlAlchemyAccessibilityFindingRepository(session).get_by_audit_job(audit_job_id)
        vision_analyses = await SqlAlchemyVisionAnalysisRepository(session).list_by_audit_job(audit_job_id)

        report_inputs = ReportInputs(
            business_name=business.name,
            category=business.category,
            website_url=business.website_url or "",
            lighthouse=_serialize(lighthouse, [
                "performance_score", "accessibility_score", "seo_score", "best_practices_score",
                "lcp_ms", "cls", "speed_index_ms", "tti_ms", "fcp_ms",
            ]),
            security=_serialize(security, [
                "https", "hsts", "csp", "x_frame_options", "mixed_content",
                "directory_listing_exposed", "hygiene_score",
            ]),
            accessibility=_serialize(accessibility, [
                "missing_alt_count", "heading_hierarchy_issues", "contrast_issues", "accessibility_score",
            ]),
            vision_summary={
                "per_device_overall_scores": {a.provider + ":" + str(a.screenshot_id): a.overall_score for a in vision_analyses}
            },
            lead_score=previous_result.get("lead_score"),
            priority=previous_result.get("priority"),
        )

        audit_job_repo = SqlAlchemyAuditJobRepository(session)
        service = ReportStageService(
            chat_provider=get_chat_provider(settings),
            storage=get_storage_backend(settings),
            report_repo=SqlAlchemyAIReportRepository(session),
            audit_job_repo=audit_job_repo,
            model=settings.DEFAULT_CHAT_MODEL,
            provider_name=settings.AI_CHAT_PROVIDER,
        )
        await service.run(
            audit_job_id=audit_job_id,
            business_id=business_id,
            report_inputs=report_inputs,
            lead_score=previous_result.get("lead_score"),
            priority=previous_result.get("priority"),
        )

        # Outreach (Phase 7) extends this chain next; for now the pipeline's
        # implemented stages end here.
        await session.commit()
        return {**previous_result, "report_generated": True}


def _serialize(model_instance, fields: list[str]) -> dict:
    if model_instance is None:
        return {}
    return {f: getattr(model_instance, f) for f in fields}


@shared_task(name="app.workers.tasks.audit.run_outreach_draft", bind=True, max_retries=2, default_retry_delay=30)
def run_outreach_draft(self, previous_result: dict) -> dict:
    try:
        return run_worker_task(_run_outreach_draft_async(previous_result))
    except Exception as exc:  # noqa: BLE001
        logger.error("outreach_draft_task_failed", previous_result=previous_result, error=str(exc))
        raise self.retry(exc=exc) from exc


async def _run_outreach_draft_async(previous_result: dict) -> dict:
    settings = get_settings()
    audit_job_id = uuid.UUID(previous_result["audit_job_id"])
    business_id = uuid.UUID(previous_result["business_id"])

    async with AsyncSessionLocal() as session:
        business = await SqlAlchemyBusinessRepository(session).get_by_id(business_id)
        if business is None:
            raise RuntimeError(f"Business {business_id} not found when drafting outreach email.")

        report = await SqlAlchemyAIReportRepository(session).get_by_audit_job(audit_job_id)
        if report is None:
            raise RuntimeError(f"No AI report found for audit job {audit_job_id}; reporting stage may have failed.")

        email_inputs = EmailInputs(
            business_name=business.name,
            category=business.category,
            sender_agency_name=settings.APP_NAME,
            executive_summary=report.executive_summary or "",
            top_improvements=(report.top_improvements or {}).get("items", []),
            lead_score=previous_result.get("lead_score"),
            priority=previous_result.get("priority"),
            template_key=DEFAULT_TEMPLATE_KEY,
        )

        audit_job_repo = SqlAlchemyAuditJobRepository(session)
        service = EmailDraftStageService(
            chat_provider=get_chat_provider(settings),
            email_repo=SqlAlchemyOutreachEmailRepository(session),
            campaign_repo=SqlAlchemyCampaignRepository(session),
            audit_job_repo=audit_job_repo,
            model=settings.DEFAULT_CHAT_MODEL,
            provider_name=settings.AI_CHAT_PROVIDER,
        )
        await service.run(
            audit_job_id=audit_job_id,
            business_id=business_id,
            organization_id=business.organization_id,
            business_name=business.name,
            report_inputs=email_inputs,
        )

        # This is the last stage of the automated pipeline.
        await audit_job_repo.mark_completed(audit_job_id)
        await session.commit()
        return {**previous_result, "email_drafted": True}


@shared_task(name="app.workers.tasks.audit.mark_pipeline_failed")
def mark_pipeline_failed(request, exc, traceback, audit_job_id: str, stage: str = "pipeline") -> None:
    """Celery ``link_error`` callback. When triggered via a chain's
    ``on_error``, Celery calls this with three positional arguments —
    (request, exc, traceback) — followed by whatever kwargs were bound via
    ``.s(audit_job_id=...)``. (An earlier version of this function assumed
    a single failed-task-id argument instead, which crashed with "got
    multiple values for argument" the first time a real pipeline failure
    exercised this path.) Records the failure — including the real
    exception message — on the AuditJob row so `GET /audits/{id}` reflects
    it even though the chain stopped short."""
    run_worker_task(_mark_failed_async(audit_job_id, stage, f"Pipeline stage failed: {exc}"))


async def _mark_failed_async(audit_job_id: str, stage: str, error_message: str) -> None:
    async with AsyncSessionLocal() as session:
        await SqlAlchemyAuditJobRepository(session).mark_failed(
            uuid.UUID(audit_job_id), stage=stage, error_message=error_message
        )
        await session.commit()


def build_audit_pipeline(audit_job_id: uuid.UUID, business_id: uuid.UUID):
    """Returns the Celery chain implementing the pipeline documented in
    ARCHITECTURE.md §4, for the stages implemented so far:
    crawl -> lighthouse -> accessibility -> security_audit ->
    technical_audit -> vision -> scoring -> reporting -> outreach_draft.
    Note: scoring runs before reporting (rather than after, as the product
    brief's stage list orders them) so the generated report can reference
    the lead score/priority — reordering two adjacent, independent stages
    for a better output beats matching the doc's ordering verbatim.
    This is the full pipeline described in the product brief; Phase 8+ adds
    the dashboard UI and hardening on top, not further pipeline stages."""
    pipeline = chain(
        run_crawl.s(str(audit_job_id), str(business_id)),
        run_lighthouse.s(),
        run_accessibility.s(),
        run_security_audit.s(),
        run_technical_audit.s(),
        run_vision.s(),
        run_scoring.s(),
        run_reporting.s(),
        run_outreach_draft.s(),
    )
    return pipeline.on_error(mark_pipeline_failed.s(audit_job_id=str(audit_job_id)))