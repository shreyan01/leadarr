from __future__ import annotations

import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin


class DeviceType(str, enum.Enum):
    DESKTOP = "desktop"
    TABLET = "tablet"
    MOBILE = "mobile"


class WebsiteSnapshot(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "website_snapshots"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    audit_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    final_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    redirect_chain: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    html_storage_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    robots_txt: Mapped[str | None] = mapped_column(Text, nullable=True)
    sitemap_urls: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    favicon_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    nav_structure: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    forms: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    buttons: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    images: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    fonts: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    js_files: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    css_files: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    crawled_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    screenshots: Mapped[list["Screenshot"]] = relationship(back_populates="snapshot", cascade="all, delete-orphan")


class Screenshot(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "screenshots"

    website_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("website_snapshots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device: Mapped[DeviceType] = mapped_column(Enum(DeviceType, name="device_type"), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)

    snapshot: Mapped["WebsiteSnapshot"] = relationship(back_populates="screenshots")
