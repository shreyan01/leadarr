from __future__ import annotations

import asyncio
import uuid

from celery import shared_task

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.repositories.audit_artifacts_repository import SqlAlchemyWebsiteSnapshotRepository
from app.repositories.audit_job_repository import SqlAlchemyAuditJobRepository
from app.repositories.business_repository import SqlAlchemyBusinessRepository
from app.services.crawl.crawl_stage_service import CrawlStageService
from app.services.crawl.crawler_service import CrawlerService
from app.utils.storage import get_storage_backend
from app.workers.celery_app import celery_app  # noqa: F401

logger = get_logger(__name__)


@shared_task(name="app.workers.tasks.crawl.run_crawl", bind=True, max_retries=2, default_retry_delay=30)
def run_crawl(self, audit_job_id: str, business_id: str) -> dict:
    try:
        return asyncio.run(_run_crawl_async(audit_job_id, business_id))
    except Exception as exc:  # noqa: BLE001
        logger.error("crawl_task_failed", audit_job_id=audit_job_id, error=str(exc))
        raise self.retry(exc=exc) from exc


async def _run_crawl_async(audit_job_id: str, business_id: str) -> dict:
    settings = get_settings()
    async with AsyncSessionLocal() as session:
        service = CrawlStageService(
            crawler=CrawlerService(get_storage_backend(settings), settings),
            snapshot_repo=SqlAlchemyWebsiteSnapshotRepository(session),
            business_repo=SqlAlchemyBusinessRepository(session),
            audit_job_repo=SqlAlchemyAuditJobRepository(session),
        )
        snapshot = await service.run(audit_job_id=uuid.UUID(audit_job_id), business_id=uuid.UUID(business_id))
        await session.commit()
        return {"audit_job_id": audit_job_id, "business_id": business_id, "final_url": snapshot.final_url}
