from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.campaign import CampaignStage


class CampaignEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_type: str
    note: str | None
    occurred_at: datetime


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    stage: CampaignStage
    next_follow_up_at: datetime | None
    events: list[CampaignEventOut] = []


class CampaignStageUpdate(BaseModel):
    stage: CampaignStage


class CampaignNoteCreate(BaseModel):
    note: str


class CampaignFollowUpUpdate(BaseModel):
    follow_up_at: datetime
