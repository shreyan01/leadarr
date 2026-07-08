from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.core.di import (
    get_accessibility_finding_repository,
    get_ai_report_repository,
    get_audit_job_repository,
    get_business_repository,
    get_lighthouse_report_repository,
    get_security_finding_repository,
    get_technical_finding_repository,
    get_vision_analysis_repository,
    get_website_snapshot_repository,
)
from app.core.exceptions import LeadForgeError, NotFoundError
from app.core.rate_limit import audit_trigger_rate_limiter
from app.core.security import Role, TokenPayload, get_current_token, require_role
from app.repositories.ai_report_repository import AIReportRepository
from app.repositories.audit_artifacts_repository import LighthouseReportRepository, WebsiteSnapshotRepository
from app.repositories.audit_job_repository import AuditJobRepository
from app.repositories.business_repository import BusinessRepository
from app.repositories.finding_repository import (
    AccessibilityFindingRepository,
    SecurityFindingRepository,
    VisionAnalysisRepository,
)
from app.repositories.technical_finding_repository import TechnicalFindingRepository
from app.schemas.audit import (
    AccessibilityFindingOut,
    AIReportOut,
    AuditJobAccepted,
    AuditJobOut,
    LighthouseReportOut,
    ScreenshotOut,
    SecurityFindingOut,
    TechnicalFindingOut,
    VisionAnalysisOut,
)
from app.workers.tasks.audit import build_audit_pipeline

router = APIRouter(tags=["audits"])


@router.post(
    "/businesses/{business_id}/audits",
    response_model=AuditJobAccepted,
    status_code=202,
    dependencies=[Depends(audit_trigger_rate_limiter)],
)
async def start_audit(
    business_id: uuid.UUID,
    token: TokenPayload = Depends(require_role(Role.OWNER, Role.ADMIN, Role.ANALYST)),
    business_repo: BusinessRepository = Depends(get_business_repository),
    audit_job_repo: AuditJobRepository = Depends(get_audit_job_repository),
):
    business = await business_repo.get_by_id(business_id)
    if business is None:
        raise NotFoundError("Business not found.")
    if not business.website_url:
        raise LeadForgeError("Business has no website_url — validate discovery first.")

    org_id = uuid.UUID(token.org) if token.org else None
    audit_job = await audit_job_repo.create(business_id=business_id, organization_id=org_id)

    build_audit_pipeline(audit_job.id, business_id).apply_async()

    return AuditJobAccepted(audit_job_id=audit_job.id, status=audit_job.status)


@router.get("/audits/{audit_job_id}", response_model=AuditJobOut)
async def get_audit(
    audit_job_id: uuid.UUID,
    token: TokenPayload = Depends(get_current_token),
    audit_job_repo: AuditJobRepository = Depends(get_audit_job_repository),
):
    job = await audit_job_repo.get_by_id(audit_job_id, with_events=True)
    if job is None:
        raise NotFoundError("Audit job not found.")
    return job


@router.get("/audits/{audit_job_id}/lighthouse", response_model=LighthouseReportOut)
async def get_lighthouse_report(
    audit_job_id: uuid.UUID,
    token: TokenPayload = Depends(get_current_token),
    repo: LighthouseReportRepository = Depends(get_lighthouse_report_repository),
):
    report = await repo.get_by_audit_job(audit_job_id)
    if report is None:
        raise NotFoundError("Lighthouse report not found for this audit job.")
    return report


@router.get("/audits/{audit_job_id}/screenshots", response_model=list[ScreenshotOut])
async def get_screenshots(
    audit_job_id: uuid.UUID,
    token: TokenPayload = Depends(get_current_token),
    repo: WebsiteSnapshotRepository = Depends(get_website_snapshot_repository),
):
    snapshot = await repo.get_by_audit_job(audit_job_id)
    if snapshot is None:
        raise NotFoundError("No website snapshot found for this audit job.")
    return snapshot.screenshots


@router.get("/audits/{audit_job_id}/accessibility", response_model=AccessibilityFindingOut)
async def get_accessibility_findings(
    audit_job_id: uuid.UUID,
    token: TokenPayload = Depends(get_current_token),
    repo: AccessibilityFindingRepository = Depends(get_accessibility_finding_repository),
):
    finding = await repo.get_by_audit_job(audit_job_id)
    if finding is None:
        raise NotFoundError("Accessibility findings not found for this audit job.")
    return finding


@router.get("/audits/{audit_job_id}/security", response_model=SecurityFindingOut)
async def get_security_findings(
    audit_job_id: uuid.UUID,
    token: TokenPayload = Depends(get_current_token),
    repo: SecurityFindingRepository = Depends(get_security_finding_repository),
):
    finding = await repo.get_by_audit_job(audit_job_id)
    if finding is None:
        raise NotFoundError("Security findings not found for this audit job.")
    return finding


@router.get("/audits/{audit_job_id}/technical", response_model=TechnicalFindingOut)
async def get_technical_findings(
    audit_job_id: uuid.UUID,
    token: TokenPayload = Depends(get_current_token),
    repo: TechnicalFindingRepository = Depends(get_technical_finding_repository),
):
    finding = await repo.get_by_audit_job(audit_job_id)
    if finding is None:
        raise NotFoundError("Technical findings not found for this audit job.")
    return finding


@router.get("/audits/{audit_job_id}/vision", response_model=list[VisionAnalysisOut])
async def get_vision_analyses(
    audit_job_id: uuid.UUID,
    token: TokenPayload = Depends(get_current_token),
    repo: VisionAnalysisRepository = Depends(get_vision_analysis_repository),
):
    analyses = await repo.list_by_audit_job(audit_job_id)
    if not analyses:
        raise NotFoundError("Vision analysis not found for this audit job.")
    return analyses


@router.get("/audits/{audit_job_id}/report", response_model=AIReportOut)
async def get_ai_report(
    audit_job_id: uuid.UUID,
    token: TokenPayload = Depends(get_current_token),
    repo: AIReportRepository = Depends(get_ai_report_repository),
):
    report = await repo.get_by_audit_job(audit_job_id)
    if report is None:
        raise NotFoundError("AI report not found for this audit job.")
    return report