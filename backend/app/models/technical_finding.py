from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class TechnicalFinding(Base, UUIDPrimaryKeyMixin):
    """Technical/on-page SEO findings not already covered by
    ``LighthouseReport`` (perf/CWV) or ``SecurityFinding`` (TLS/headers) —
    the file-presence and structural checks from the product spec's
    passive-analysis list."""

    __tablename__ = "technical_findings"

    audit_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    page_load_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    sitemap_present: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    robots_present: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    favicon_present: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    schema_markup_present: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    schema_markup_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    open_graph_present: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    twitter_card_present: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    google_business_link: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    broken_links: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    broken_links_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    oversized_images: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    oversized_images_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    technical_score: Mapped[int | None] = mapped_column(Integer, nullable=True)