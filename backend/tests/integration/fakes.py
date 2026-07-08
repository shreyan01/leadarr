"""In-memory fakes implementing the same repository Protocols as the real
SQLAlchemy repositories. Used to integration-test the API layer (routing,
DI wiring, request/response schemas, auth) without a real database — this
is the payoff of the repository-interface pattern from ARCHITECTURE.md §2.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.models.business import Business, BusinessStatus
from app.models.user import Organization, Role, User


class FakeUserRepository:
    def __init__(self) -> None:
        self.users: dict[uuid.UUID, User] = {}
        self.organizations: dict[uuid.UUID, Organization] = {}

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self.users.values() if u.email == email), None)

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.users.get(user_id)

    async def create_with_organization(
        self, *, organization_name: str, full_name: str, email: str, hashed_password: str
    ) -> User:
        org = Organization(id=uuid.uuid4(), name=organization_name, plan="free", is_active=True)
        self.organizations[org.id] = org
        user = User(
            id=uuid.uuid4(),
            organization_id=org.id,
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            role=Role.OWNER,
            is_active=True,
        )
        self.users[user.id] = user
        return user


class FakeBusinessRepository:
    def __init__(self) -> None:
        self.businesses: dict[uuid.UUID, Business] = {}

    async def get_by_id(self, business_id: uuid.UUID) -> Business | None:
        return self.businesses.get(business_id)

    async def find_by_place_id(self, *, organization_id, google_place_id: str) -> Business | None:
        return next(
            (
                b
                for b in self.businesses.values()
                if b.organization_id == organization_id and b.google_place_id == google_place_id
            ),
            None,
        )

    async def upsert_discovered(self, *, organization_id, data: dict) -> Business:
        business = Business(
            id=uuid.uuid4(),
            organization_id=organization_id,
            discovered_at=datetime.now(timezone.utc),
            status=BusinessStatus.DISCOVERED,
            **data,
        )
        self.businesses[business.id] = business
        return business

    async def list_filtered(
        self, *, organization_id, city=None, category=None, status=None, page=1, page_size=20
    ):
        items = [b for b in self.businesses.values() if b.organization_id == organization_id]
        if city:
            items = [b for b in items if city.lower() in b.city.lower()]
        if category:
            items = [b for b in items if category.lower() in b.category.lower()]
        if status:
            items = [b for b in items if b.status == status]
        total = len(items)
        start = (page - 1) * page_size
        return items[start : start + page_size], total

    async def update_status(self, business_id: uuid.UUID, status: BusinessStatus) -> Business | None:
        business = self.businesses.get(business_id)
        if business is None:
            return None
        business.status = status
        return business

    async def delete(self, business_id: uuid.UUID) -> bool:
        if business_id not in self.businesses:
            return False
        del self.businesses[business_id]
        return True