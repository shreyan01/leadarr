from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import Business, BusinessStatus


class BusinessRepository(Protocol):
    async def get_by_id(self, business_id: uuid.UUID) -> Business | None: ...

    async def find_by_place_id(
        self, *, organization_id: uuid.UUID | None, google_place_id: str
    ) -> Business | None: ...

    async def upsert_discovered(self, *, organization_id: uuid.UUID | None, data: dict) -> Business: ...

    async def list_filtered(
        self,
        *,
        organization_id: uuid.UUID | None,
        city: str | None = None,
        category: str | None = None,
        status: BusinessStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Business], int]: ...

    async def update_status(self, business_id: uuid.UUID, status: BusinessStatus) -> Business | None: ...

    async def update_email(self, business_id: uuid.UUID, email: str) -> Business | None: ...

    async def update(self, business_id: uuid.UUID, data: dict) -> Business | None: ...

    async def delete(self, business_id: uuid.UUID) -> bool: ...


class SqlAlchemyBusinessRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, business_id: uuid.UUID) -> Business | None:
        result = await self._session.execute(select(Business).where(Business.id == business_id))
        return result.scalar_one_or_none()

    async def find_by_place_id(
        self, *, organization_id: uuid.UUID | None, google_place_id: str
    ) -> Business | None:
        stmt = select(Business).where(
            Business.organization_id == organization_id, Business.google_place_id == google_place_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_discovered(self, *, organization_id: uuid.UUID | None, data: dict) -> Business:
        existing = None
        if data.get("google_place_id"):
            existing = await self.find_by_place_id(
                organization_id=organization_id, google_place_id=data["google_place_id"]
            )

        if existing is not None:
            for field in (
                "name", "category", "phone", "address", "website_url",
                "google_rating", "review_count", "latitude", "longitude",
            ):
                if data.get(field) is not None:
                    setattr(existing, field, data[field])
            await self._session.flush()
            return existing

        business = Business(
            organization_id=organization_id,
            discovered_at=datetime.now(timezone.utc),
            status=BusinessStatus.DISCOVERED,
            **data,
        )
        self._session.add(business)
        await self._session.flush()
        return business

    async def list_filtered(
        self,
        *,
        organization_id: uuid.UUID | None,
        city: str | None = None,
        category: str | None = None,
        status: BusinessStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Business], int]:
        stmt = select(Business).where(Business.organization_id == organization_id)
        count_stmt = select(func.count()).select_from(Business).where(Business.organization_id == organization_id)

        if city:
            stmt = stmt.where(Business.city.ilike(f"%{city}%"))
            count_stmt = count_stmt.where(Business.city.ilike(f"%{city}%"))
        if category:
            stmt = stmt.where(Business.category.ilike(f"%{category}%"))
            count_stmt = count_stmt.where(Business.category.ilike(f"%{category}%"))
        if status:
            stmt = stmt.where(Business.status == status)
            count_stmt = count_stmt.where(Business.status == status)

        stmt = stmt.order_by(Business.discovered_at.desc()).offset((page - 1) * page_size).limit(page_size)

        total = (await self._session.execute(count_stmt)).scalar_one()
        rows = (await self._session.execute(stmt)).scalars().all()
        return list(rows), total

    async def update_status(self, business_id: uuid.UUID, status: BusinessStatus) -> Business | None:
        business = await self.get_by_id(business_id)
        if business is None:
            return None
        business.status = status
        await self._session.flush()
        return business

    async def update_email(self, business_id: uuid.UUID, email: str) -> Business | None:
        business = await self.get_by_id(business_id)
        if business is None:
            return None
        business.email = email
        await self._session.flush()
        return business

    async def update(self, business_id: uuid.UUID, data: dict) -> Business | None:
        business = await self.get_by_id(business_id)
        if business is None:
            return None
        for field, value in data.items():
            setattr(business, field, value)
        await self._session.flush()
        return business

    async def delete(self, business_id: uuid.UUID) -> bool:
        business = await self.get_by_id(business_id)
        if business is None:
            return False
        # Audit jobs, campaigns, and outreach emails all have
        # ondelete="CASCADE" foreign keys back to businesses (see their
        # models), so deleting the business row cleans up everything
        # derived from it in one operation — no orphaned data left behind.
        await self._session.delete(business)
        await self._session.flush()
        return True