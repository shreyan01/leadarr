from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.outreach_email import EmailStatus


class EmailDraftRequest(BaseModel):
    template_key: str = Field(default="default")


class OutreachEmailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    template_key: str
    subject: str
    body_text: str
    body_html: str | None
    status: EmailStatus
    created_at: datetime


class EmailUpdateRequest(BaseModel):
    subject: str | None = None
    body_text: str | None = None
    body_html: str | None = None


class EmailSendRequest(BaseModel):
    to_address: EmailStr
