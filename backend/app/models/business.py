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
    # Fallback contact channels — populated when discovery finds them even
    # without a proper website (e.g. OSM tags a phone/email/social page but
    # no `website`). A business with only a Facebook/Instagram presence is
    # still a real lead — arguably a *better* one, since it shows they've
    # already tried to be findable online and just never got a real site —
    # so these are captured rather than discarded, not treated as noise.
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    facebook_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    instagram_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    google_place_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_rating: Mapped[float | None] = mapped_column(Numeric(2, 1), nullable=True)
    review_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    discovery_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    discovered_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[BusinessStatus] = mapped_column(
        Enum(BusinessStatus, name="business_status"), default=BusinessStatus.DISCOVERED, nullable=False
    )

    audit_jobs: Mapped[list["AuditJob"]] = relationship(back_populates="business")

    @property
    def has_auditable_website(self) -> bool:
        """False for social-only leads — the audit pipeline (Lighthouse,
        security, screenshots) needs a real site; auditing a Facebook page
        would just be a report about Facebook's engineering, not theirs."""
        return bool(self.website_url)

    @property
    def is_social_only_lead(self) -> bool:
        """A business with no website but a captured Facebook/Instagram/
        phone/email — a distinct, high-opportunity lead category (the
        classic "you don't even have a website yet" pitch), not a dead end."""
        return not self.website_url and bool(
            self.facebook_url or self.instagram_url or self.phone or self.email
        )