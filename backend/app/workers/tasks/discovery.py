from __future__ import annotations

import asyncio
import uuid

from celery import shared_task

from app.adapters.discovery.registry import get_discovery_provider
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.repositories.business_repository import SqlAlchemyBusinessRepository
from app.services.discovery.discovery_service import DiscoveryService
from app.services.validation.validation_service import WebsiteValidationService
from app.workers.celery_app import celery_app  # noqa: F401  (ensures app is configured before task registration)

logger = get_logger(__name__)


@shared_task(name="app.workers.tasks.discovery.run_discovery", bind=True, max_retries=3, default_retry_delay=30)
def run_discovery(
    self,
    *,
    organization_id: str | None,
    country: str,
    city: str,
    category: str,
    limit: int = 20,
) -> dict:
    """Celery entrypoint — runs the async discovery pipeline to completion
    inside a fresh event loop, since Celery workers are synchronous."""
    try:
        return asyncio.run(_run_discovery_async(organization_id, country, city, category, limit))
    except Exception as exc:  # noqa: BLE001 — deliberately broad: this is the task boundary
        logger.error("discovery_task_failed", error=str(exc), city=city, category=category)
        raise self.retry(exc=exc) from exc


async def _run_discovery_async(
    organization_id: str | None, country: str, city: str, category: str, limit: int
) -> dict:
    settings = get_settings()
    async with AsyncSessionLocal() as session:
        repo = SqlAlchemyBusinessRepository(session)
        service = DiscoveryService(
            provider=get_discovery_provider(settings),
            business_repo=repo,
            validation_service=WebsiteValidationService(),
            settings=settings,
        )
        org_uuid = uuid.UUID(organization_id) if organization_id else None
        businesses = await service.discover_and_persist(
            organization_id=org_uuid, country=country, city=city, category=category, limit=limit
        )
        await session.commit()
        return {"discovered_count": len(businesses), "business_ids": [str(b.id) for b in businesses]}
