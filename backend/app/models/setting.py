from __future__ import annotations

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, OrgScopedMixin, UUIDPrimaryKeyMixin


class Setting(Base, UUIDPrimaryKeyMixin, OrgScopedMixin):
    __tablename__ = "settings"
    __table_args__ = (UniqueConstraint("organization_id", "key", name="uq_setting_org_key"),)

    key: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
