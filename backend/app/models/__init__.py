"""Import every model here so ``Base.metadata`` is complete for Alembic
autogenerate and for ``Base.metadata.create_all`` in tests."""
from app.models.accessibility_finding import AccessibilityFinding
from app.models.ai_report import AIReport
from app.models.audit_job import AuditJob, JobEvent
from app.models.business import Business
from app.models.campaign import Campaign, CampaignEvent
from app.models.lead_score import LeadScore
from app.models.lighthouse_report import LighthouseReport
from app.models.outreach_email import OutreachEmail
from app.models.security_finding import SecurityFinding
from app.models.setting import Setting
from app.models.technical_finding import TechnicalFinding
from app.models.user import Organization, User
from app.models.vision_analysis import VisionAnalysis
from app.models.website_snapshot import Screenshot, WebsiteSnapshot

__all__ = [
    "AccessibilityFinding",
    "AIReport",
    "AuditJob",
    "JobEvent",
    "Business",
    "Campaign",
    "CampaignEvent",
    "LeadScore",
    "LighthouseReport",
    "OutreachEmail",
    "SecurityFinding",
    "Setting",
    "TechnicalFinding",
    "Organization",
    "User",
    "VisionAnalysis",
    "Screenshot",
    "WebsiteSnapshot",
]