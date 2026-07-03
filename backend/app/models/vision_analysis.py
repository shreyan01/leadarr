from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class VisionAnalysis(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "vision_analyses"

    audit_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    screenshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("screenshots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)

    trust_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    professionalism_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    modernity_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    whitespace_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    typography_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    layout_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    visual_hierarchy_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cta_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    conversion_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    brand_consistency_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nav_clarity_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mobile_friendliness_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    overall_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    raw_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
