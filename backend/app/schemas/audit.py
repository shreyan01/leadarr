from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.audit_job import AuditStatus, JobEventStatus


class AuditJobAccepted(BaseModel):
    audit_job_id: uuid.UUID
    status: AuditStatus = AuditStatus.PENDING


class JobEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    stage: str
    status: JobEventStatus
    duration_ms: int | None
    retries: int
    model_used: str | None
    message: str | None
    created_at: datetime


class AuditJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    status: AuditStatus
    current_stage: str | None
    failed_stage: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    events: list[JobEventOut] = []


class LighthouseReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    performance_score: int | None
    accessibility_score: int | None
    seo_score: int | None
    best_practices_score: int | None
    lcp_ms: float | None
    cls: float | None
    speed_index_ms: float | None
    tti_ms: float | None
    fcp_ms: float | None


class ScreenshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    device: str
    storage_path: str
    width: int
    height: int


class AIReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    executive_summary: str | None
    technical_summary: str | None
    business_summary: str | None
    seo_summary: str | None
    accessibility_summary: str | None
    security_summary: str | None
    design_summary: str | None
    top_improvements: dict | None
    estimated_effort: dict | None
    priority_fixes: dict | None
    estimated_business_impact: str | None
    markdown_storage_path: str | None
    html_storage_path: str | None


class VisionAnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    screenshot_id: uuid.UUID
    provider: str
    model: str
    trust_score: int | None
    professionalism_score: int | None
    modernity_score: int | None
    whitespace_score: int | None
    typography_score: int | None
    layout_score: int | None
    visual_hierarchy_score: int | None
    cta_score: int | None
    conversion_score: int | None
    brand_consistency_score: int | None
    nav_clarity_score: int | None
    mobile_friendliness_score: int | None
    overall_score: int | None


class AccessibilityFindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    missing_alt_count: int | None
    heading_hierarchy_issues: dict | None
    aria_issues: dict | None
    contrast_issues: dict | None
    unlabeled_buttons: dict | None
    keyboard_nav_issues: dict | None
    unlabeled_form_fields: dict | None
    accessibility_score: int | None


class SecurityFindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    https: bool | None
    tls_version: str | None
    cert_issuer: str | None
    cert_expires_at: datetime | None
    hsts: bool | None
    csp: str | None
    permissions_policy: str | None
    referrer_policy: str | None
    x_frame_options: str | None
    x_content_type_options: str | None
    cookie_flags: dict | None
    mixed_content: bool | None
    directory_listing_exposed: bool | None
    exposed_source_maps: dict | None
    exposed_config_files: dict | None
    exposed_secrets_regex_hits: dict | None
    server_header: str | None
    compression: str | None
    caching_headers: dict | None
    public_api_endpoints: dict | None
    manifest_present: bool | None
    service_worker_present: bool | None
    hygiene_score: int | None