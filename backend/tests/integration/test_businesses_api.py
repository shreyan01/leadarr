from __future__ import annotations

from fastapi.testclient import TestClient


class TestBusinessesApi:
    def test_create_and_get_business(self, client: TestClient, auth_headers: dict[str, str]):
        create_response = client.post(
            "/api/v1/businesses",
            json={
                "name": "Acme Roofing",
                "category": "Roofing",
                "city": "Austin",
                "country": "United States",
                "website_url": "https://acmeroofing.example.com",
            },
            headers=auth_headers,
        )
        assert create_response.status_code == 201
        business_id = create_response.json()["id"]

        get_response = client.get(f"/api/v1/businesses/{business_id}", headers=auth_headers)
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "Acme Roofing"
        assert get_response.json()["status"] == "discovered"

    def test_get_nonexistent_business_returns_404(self, client: TestClient, auth_headers: dict[str, str]):
        response = client.get("/api/v1/businesses/00000000-0000-0000-0000-000000000000", headers=auth_headers)
        assert response.status_code == 404

    def test_list_businesses_filters_by_city(self, client: TestClient, auth_headers: dict[str, str]):
        for city in ("Austin", "Dallas"):
            client.post(
                "/api/v1/businesses",
                json={"name": f"Biz {city}", "category": "Roofing", "city": city, "country": "United States"},
                headers=auth_headers,
            )

        response = client.get("/api/v1/businesses", params={"city": "Austin"}, headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["city"] == "Austin"

    def test_archive_business_updates_status(self, client: TestClient, auth_headers: dict[str, str]):
        create_response = client.post(
            "/api/v1/businesses",
            json={"name": "Acme Roofing", "category": "Roofing", "city": "Austin", "country": "United States"},
            headers=auth_headers,
        )
        business_id = create_response.json()["id"]

        archive_response = client.patch(f"/api/v1/businesses/{business_id}/archive", headers=auth_headers)
        assert archive_response.status_code == 200
        assert archive_response.json()["status"] == "archived"

    def test_businesses_require_authentication(self, client: TestClient):
        response = client.get("/api/v1/businesses")
        assert response.status_code == 401
