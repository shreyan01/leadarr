from __future__ import annotations

from fastapi.testclient import TestClient


class TestAuthFlow:
    def test_register_returns_tokens(self, client: TestClient):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "organization_name": "Acme Agency",
                "full_name": "Ada Lovelace",
                "email": "ada@acme-agency.dev",
                "password": "correct-horse-battery",
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body

    def test_duplicate_registration_is_rejected(self, client: TestClient):
        payload = {
            "organization_name": "Acme Agency",
            "full_name": "Ada Lovelace",
            "email": "dupe@acme-agency.dev",
            "password": "correct-horse-battery",
        }
        first = client.post("/api/v1/auth/register", json=payload)
        assert first.status_code == 201

        second = client.post("/api/v1/auth/register", json=payload)
        assert second.status_code == 409

    def test_me_returns_profile_when_authenticated(self, client: TestClient, auth_headers: dict[str, str]):
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["email"] == "ada@acme-agency.dev"

    def test_me_rejects_missing_token(self, client: TestClient):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_login_with_wrong_password_is_rejected(self, client: TestClient, auth_headers: dict[str, str]):
        response = client.post("/api/v1/auth/login", json={"email": "ada@acme-agency.dev", "password": "wrong-password"})
        assert response.status_code == 422

    def test_login_with_correct_password_succeeds(self, client: TestClient, auth_headers: dict[str, str]):
        response = client.post(
            "/api/v1/auth/login", json={"email": "ada@acme-agency.dev", "password": "correct-horse-battery"}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
