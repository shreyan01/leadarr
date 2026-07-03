from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outreach_email import OutreachEmail


class OutreachEmailRepository(Protocol):
    async def create(self, email: OutreachEmail) -> OutreachEmail: ...
    async def get_by_id(self, email_id: uuid.UUID) -> OutreachEmail | None: ...
    async def list_by_business(self, business_id: uuid.UUID) -> list[OutreachEmail]: ...
    async def update(self, email: OutreachEmail) -> OutreachEmail: ...


class SqlAlchemyOutreachEmailRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, email: OutreachEmail) -> OutreachEmail:
        self._session.add(email)
        await self._session.flush()
        return email

    async def get_by_id(self, email_id: uuid.UUID) -> OutreachEmail | None:
        result = await self._session.execute(select(OutreachEmail).where(OutreachEmail.id == email_id))
        return result.scalar_one_or_none()

    async def list_by_business(self, business_id: uuid.UUID) -> list[OutreachEmail]:
        stmt = (
            select(OutreachEmail)
            .where(OutreachEmail.business_id == business_id)
            .order_by(OutreachEmail.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, email: OutreachEmail) -> OutreachEmail:
        await self._session.flush()
        return email
