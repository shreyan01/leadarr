from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class LighthouseReport(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "lighthouse_reports"

    audit_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    raw_json_storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)

    performance_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accessibility_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seo_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    best_practices_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    lcp_ms: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    cls: Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)
    speed_index_ms: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    tti_ms: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    fcp_ms: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
