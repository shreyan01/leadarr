from __future__ import annotations

import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class SecurityFinding(Base, UUIDPrimaryKeyMixin):
    """Passive security hygiene snapshot — never populated via active probing.

    See ARCHITECTURE.md §1 and services/security_audit/passive_http_client.py
    for the guardrails that keep this table's producer read-only.
    """

    __tablename__ = "security_findings"

    audit_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    https: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    tls_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cert_issuer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cert_expires_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    hsts: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    csp: Mapped[str | None] = mapped_column(Text, nullable=True)
    permissions_policy: Mapped[str | None] = mapped_column(Text, nullable=True)
    referrer_policy: Mapped[str | None] = mapped_column(Text, nullable=True)
    x_frame_options: Mapped[str | None] = mapped_column(Text, nullable=True)
    x_content_type_options: Mapped[str | None] = mapped_column(Text, nullable=True)

    cookie_flags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    mixed_content: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    directory_listing_exposed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    exposed_source_maps: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    exposed_config_files: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    exposed_secrets_regex_hits: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    tech_fingerprint: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    server_header: Mapped[str | None] = mapped_column(Text, nullable=True)
    compression: Mapped[str | None] = mapped_column(Text, nullable=True)
    caching_headers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    public_api_endpoints: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    manifest_present: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    service_worker_present: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    hygiene_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
