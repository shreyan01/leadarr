from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.di import get_business_repository, get_user_repository
from app.core.rate_limit import audit_trigger_rate_limiter, auth_rate_limiter
from app.main import app
from tests.integration.fakes import FakeBusinessRepository, FakeUserRepository


async def _noop() -> None:
    return None


@pytest.fixture
def fake_user_repo() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture
def fake_business_repo() -> FakeBusinessRepository:
    return FakeBusinessRepository()


@pytest.fixture
def client(fake_user_repo: FakeUserRepository, fake_business_repo: FakeBusinessRepository):
    app.dependency_overrides[get_user_repository] = lambda: fake_user_repo
    app.dependency_overrides[get_business_repository] = lambda: fake_business_repo
    # No Redis in the test environment — rate limiting is exercised by its
    # own unit-style test against RateLimiter directly (see test_rate_limit.py).
    app.dependency_overrides[auth_rate_limiter] = _noop
    app.dependency_overrides[audit_trigger_rate_limiter] = _noop
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Acme Agency",
            "full_name": "Ada Lovelace",
            "email": "ada@acme-agency.dev",
            "password": "correct-horse-battery",
        },
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
