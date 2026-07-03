from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.lead_score import LeadPriority


class LeadScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    business_id: uuid.UUID
    audit_job_id: uuid.UUID
    performance_component: float | None
    security_component: float | None
    accessibility_component: float | None
    seo_component: float | None
    design_component: float | None
    business_rating_component: float | None
    review_count_component: float | None
    website_age_component: float | None
    technology_component: float | None
    overall_score: float
    priority: LeadPriority
    scored_at: datetime


class LeadListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    business_id: uuid.UUID
    overall_score: float
    priority: LeadPriority
    scored_at: datetime


class LeadListResponse(BaseModel):
    items: list[LeadListItem]
    total: int
    page: int
    page_size: int
