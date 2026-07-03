from __future__ import annotations

import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class LeadPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class LeadScore(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "lead_scores"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    audit_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    performance_component: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    security_component: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    accessibility_component: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    seo_component: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    design_component: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    business_rating_component: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    review_count_component: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    website_age_component: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    technology_component: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    overall_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, index=True)
    priority: Mapped[LeadPriority] = mapped_column(Enum(LeadPriority, name="lead_priority"), nullable=False, index=True)
    scored_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
