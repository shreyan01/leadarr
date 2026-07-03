from __future__ import annotations

import enum

from sqlalchemy import DateTime, Enum, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, OrgScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class BusinessStatus(str, enum.Enum):
    DISCOVERED = "discovered"
    VALIDATED = "validated"
    AUDITED = "audited"
    ARCHIVED = "archived"


class Business(Base, UUIDPrimaryKeyMixin, TimestampMixin, OrgScopedMixin):
    __tablename__ = "businesses"
    __table_args__ = (
        UniqueConstraint("organization_id", "google_place_id", name="uq_business_org_place"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(120), nullable=False)

    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)

    website_url: Mapped[str | None] = mapped_column(String(1000), nullable=True, index=True)
    google_place_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_rating: Mapped[float | None] = mapped_column(Numeric(2, 1), nullable=True)
    review_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    discovery_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    discovered_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[BusinessStatus] = mapped_column(
        Enum(BusinessStatus, name="business_status"), default=BusinessStatus.DISCOVERED, nullable=False
    )

    audit_jobs: Mapped[list["AuditJob"]] = relationship(back_populates="business")
