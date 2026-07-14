from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.business import BusinessStatus


class DiscoveryRequest(BaseModel):
    country: str = Field(min_length=2, max_length=120)
    city: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=120)
    limit: int = Field(default=20, ge=1, le=20)


class DiscoveryJobAccepted(BaseModel):
    task_id: str
    status: str = "queued"


class DiscoveryJobStatus(BaseModel):
    task_id: str
    status: str
    discovered_count: int | None = None
    error: str | None = None


class BusinessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: str
    phone: str | None
    email: str | None
    address: str | None
    city: str
    country: str
    latitude: float | None
    longitude: float | None
    website_url: str | None
    facebook_url: str | None
    instagram_url: str | None
    google_rating: float | None
    review_count: int | None
    status: BusinessStatus
    discovered_at: datetime | None
    is_social_only_lead: bool


class BusinessListResponse(BaseModel):
    items: list[BusinessOut]
    total: int
    page: int
    page_size: int


class BusinessUpdate(BaseModel):
    """All fields optional — only what's provided gets changed. The main
    use case: adding a website_url you found yourself to a business that
    was discovered without one (common for OSM discoveries, which often
    lack that field even for businesses that do have a real site)."""

    name: str | None = None
    category: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    website_url: str | None = None