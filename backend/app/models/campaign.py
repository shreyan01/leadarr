from __future__ import annotations

import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, OrgScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class CampaignStage(str, enum.Enum):
    DISCOVERED = "discovered"
    AUDITED = "audited"
    EMAIL_DRAFTED = "email_drafted"
    SENT = "sent"
    OPENED = "opened"
    CLICKED = "clicked"
    RESPONDED = "responded"
    MEETING_SCHEDULED = "meeting_scheduled"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"
    ARCHIVED = "archived"


class Campaign(Base, UUIDPrimaryKeyMixin, TimestampMixin, OrgScopedMixin):
    __tablename__ = "campaigns"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    stage: Mapped[CampaignStage] = mapped_column(
        Enum(CampaignStage, name="campaign_stage"), default=CampaignStage.DISCOVERED, nullable=False, index=True
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    next_follow_up_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    events: Mapped[list["CampaignEvent"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")


class CampaignEvent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "campaign_events"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    campaign: Mapped["Campaign"] = relationship(back_populates="events")
