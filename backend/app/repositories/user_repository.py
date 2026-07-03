from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Organization, User


class UserRepository(Protocol):
    async def get_by_email(self, email: str) -> User | None: ...
    async def get_by_id(self, user_id: uuid.UUID) -> User | None: ...
    async def create_with_organization(
        self, *, organization_name: str, full_name: str, email: str, hashed_password: str
    ) -> User: ...


class SqlAlchemyUserRepository:
    """Concrete UserRepository backed by SQLAlchemy async session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create_with_organization(
        self, *, organization_name: str, full_name: str, email: str, hashed_password: str
    ) -> User:
        from app.models.user import Role

        org = Organization(name=organization_name)
        self._session.add(org)
        await self._session.flush()  # populate org.id

        user = User(
            organization_id=org.id,
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            role=Role.OWNER,
        )
        self._session.add(user)
        await self._session.flush()
        return user
