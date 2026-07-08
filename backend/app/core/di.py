"""Central place where request-scoped dependencies are wired together.

Keeping construction here (rather than importing concrete classes inside
routers) is what lets us swap a repository or provider implementation
without touching API code.
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.discovery.registry import get_discovery_provider
from app.adapters.email.registry import get_email_sender
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.repositories.ai_report_repository import AIReportRepository, SqlAlchemyAIReportRepository
from app.repositories.audit_artifacts_repository import (
    LighthouseReportRepository,
    SqlAlchemyLighthouseReportRepository,
    SqlAlchemyWebsiteSnapshotRepository,
    WebsiteSnapshotRepository,
)
from app.repositories.audit_job_repository import AuditJobRepository, SqlAlchemyAuditJobRepository
from app.repositories.business_repository import BusinessRepository, SqlAlchemyBusinessRepository
from app.repositories.campaign_repository import CampaignRepository, SqlAlchemyCampaignRepository
from app.repositories.finding_repository import (
    AccessibilityFindingRepository,
    SecurityFindingRepository,
    SqlAlchemyAccessibilityFindingRepository,
    SqlAlchemySecurityFindingRepository,
    SqlAlchemyVisionAnalysisRepository,
    VisionAnalysisRepository,
)
from app.repositories.lead_score_repository import LeadScoreRepository, SqlAlchemyLeadScoreRepository
from app.repositories.outreach_email_repository import OutreachEmailRepository, SqlAlchemyOutreachEmailRepository
from app.repositories.technical_finding_repository import (
    SqlAlchemyTechnicalFindingRepository,
    TechnicalFindingRepository,
)
from app.repositories.user_repository import SqlAlchemyUserRepository, UserRepository
from app.services.outreach.email_send_service import EmailSendService
from app.services.auth_service import AuthService
from app.services.discovery.discovery_service import DiscoveryService
from app.services.validation.validation_service import WebsiteValidationService


def get_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    return AuthService(user_repo, settings)


def get_business_repository(session: AsyncSession = Depends(get_db)) -> BusinessRepository:
    return SqlAlchemyBusinessRepository(session)


def get_validation_service() -> WebsiteValidationService:
    return WebsiteValidationService()


def get_discovery_service(
    business_repo: BusinessRepository = Depends(get_business_repository),
    validation_service: WebsiteValidationService = Depends(get_validation_service),
    settings: Settings = Depends(get_settings),
) -> DiscoveryService:
    return DiscoveryService(get_discovery_provider(settings), business_repo, validation_service, settings)


def get_audit_job_repository(session: AsyncSession = Depends(get_db)) -> AuditJobRepository:
    return SqlAlchemyAuditJobRepository(session)


def get_website_snapshot_repository(session: AsyncSession = Depends(get_db)) -> WebsiteSnapshotRepository:
    return SqlAlchemyWebsiteSnapshotRepository(session)


def get_lighthouse_report_repository(session: AsyncSession = Depends(get_db)) -> LighthouseReportRepository:
    return SqlAlchemyLighthouseReportRepository(session)


def get_accessibility_finding_repository(session: AsyncSession = Depends(get_db)) -> AccessibilityFindingRepository:
    return SqlAlchemyAccessibilityFindingRepository(session)


def get_security_finding_repository(session: AsyncSession = Depends(get_db)) -> SecurityFindingRepository:
    return SqlAlchemySecurityFindingRepository(session)


def get_vision_analysis_repository(session: AsyncSession = Depends(get_db)) -> VisionAnalysisRepository:
    return SqlAlchemyVisionAnalysisRepository(session)


def get_ai_report_repository(session: AsyncSession = Depends(get_db)) -> AIReportRepository:
    return SqlAlchemyAIReportRepository(session)


def get_lead_score_repository(session: AsyncSession = Depends(get_db)) -> LeadScoreRepository:
    return SqlAlchemyLeadScoreRepository(session)


def get_technical_finding_repository(session: AsyncSession = Depends(get_db)) -> TechnicalFindingRepository:
    return SqlAlchemyTechnicalFindingRepository(session)


def get_outreach_email_repository(session: AsyncSession = Depends(get_db)) -> OutreachEmailRepository:
    return SqlAlchemyOutreachEmailRepository(session)


def get_campaign_repository(session: AsyncSession = Depends(get_db)) -> CampaignRepository:
    return SqlAlchemyCampaignRepository(session)


def get_email_send_service(
    email_repo: OutreachEmailRepository = Depends(get_outreach_email_repository),
    campaign_repo: CampaignRepository = Depends(get_campaign_repository),
    settings: Settings = Depends(get_settings),
) -> EmailSendService:
    return EmailSendService(get_email_sender(settings), email_repo, campaign_repo, settings.EMAIL_FROM_ADDRESS)