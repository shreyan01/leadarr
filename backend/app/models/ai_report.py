from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class AIReport(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "ai_reports"

    audit_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)

    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    technical_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    seo_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    accessibility_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    security_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    design_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    top_improvements: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    estimated_effort: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    priority_fixes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    estimated_business_impact: Mapped[str | None] = mapped_column(Text, nullable=True)

    markdown_storage_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    html_storage_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
