"""Load test for LeadForge's read-heavy endpoints (the ones a dashboard
hammers on every page load). Discovery/audit-trigger endpoints are
deliberately excluded — those fan out into Celery/Playwright/Lighthouse
work and shouldn't be load-tested by spamming real target websites.

Usage:
    pip install locust
    locust -f infra/load-test/locustfile.py --host http://localhost:8000

Then open http://localhost:8089 to configure users/spawn-rate and start.
"""
from __future__ import annotations

import random

from locust import HttpUser, between, task


class DashboardUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self) -> None:
        suffix = random.randint(1, 10_000_000)
        register_payload = {
            "organization_name": f"Load Test Agency {suffix}",
            "full_name": "Load Test User",
            "email": f"loadtest{suffix}@example-agency.dev",
            "password": "correct-horse-battery-staple",
        }
        response = self.client.post("/api/v1/auth/register", json=register_payload)
        tokens = response.json()
        self.headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    @task(3)
    def list_businesses(self) -> None:
        self.client.get("/api/v1/businesses", headers=self.headers)

    @task(3)
    def list_leads(self) -> None:
        self.client.get("/api/v1/leads", headers=self.headers)

    @task(2)
    def list_campaigns(self) -> None:
        self.client.get("/api/v1/campaigns", headers=self.headers)

    @task(1)
    def monitoring_stats(self) -> None:
        self.client.get("/api/v1/monitoring/stats", headers=self.headers)

    @task(1)
    def health(self) -> None:
        self.client.get("/api/v1/health")
