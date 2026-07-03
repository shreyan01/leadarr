from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class AccessibilityFinding(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "accessibility_findings"

    audit_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    missing_alt_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heading_hierarchy_issues: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    aria_issues: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    contrast_issues: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    unlabeled_buttons: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    keyboard_nav_issues: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    unlabeled_form_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    accessibility_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
