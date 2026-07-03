from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import audits, auth, businesses, campaigns, discovery, emails, health, leads, monitoring

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(health.router)
api_router.include_router(discovery.router)
api_router.include_router(businesses.router)
api_router.include_router(audits.router)
api_router.include_router(leads.router)
api_router.include_router(emails.router)
api_router.include_router(campaigns.router)
api_router.include_router(monitoring.router)
