from __future__ import annotations

import uuid

from app.core.exceptions import LeadForgeError
from app.core.logging import get_logger
from app.models.audit_job import JobEventStatus
from app.models.website_snapshot import DeviceType, Screenshot, WebsiteSnapshot
from app.repositories.audit_artifacts_repository import WebsiteSnapshotRepository
from app.repositories.audit_job_repository import AuditJobRepository
from app.repositories.business_repository import BusinessRepository
from app.services.crawl.crawler_service import CrawlerService
from app.utils.stage_timer import stage_timer

logger = get_logger(__name__)

STAGE_NAME = "crawl"


class CrawlStageService:
    def __init__(
        self,
        crawler: CrawlerService,
        snapshot_repo: WebsiteSnapshotRepository,
        business_repo: BusinessRepository,
        audit_job_repo: AuditJobRepository,
    ) -> None:
        self._crawler = crawler
        self._snapshots = snapshot_repo
        self._businesses = business_repo
        self._audit_jobs = audit_job_repo

    async def run(self, *, audit_job_id: uuid.UUID, business_id: uuid.UUID) -> WebsiteSnapshot:
        await self._audit_jobs.mark_stage_started(audit_job_id, STAGE_NAME)

        business = await self._businesses.get_by_id(business_id)
        if business is None or not business.website_url:
            raise LeadForgeError(f"Business {business_id} has no validated website_url to crawl.")

        with stage_timer() as elapsed_ms:
            try:
                result = await self._crawler.crawl(
                    url=business.website_url, business_id=business_id, audit_job_id=audit_job_id
                )
            except Exception as exc:
                await self._audit_jobs.log_event(
                    audit_job_id=audit_job_id, stage=STAGE_NAME, status=JobEventStatus.FAILED,
                    duration_ms=elapsed_ms(), message=str(exc)[:1000],
                )
                raise

            snapshot = WebsiteSnapshot(
                business_id=business_id,
                audit_job_id=audit_job_id,
                final_url=result.final_url,
                http_status=result.http_status,
                redirect_chain={"chain": result.redirect_chain},
                html_storage_path=result.html_storage_path,
                robots_txt=result.robots_txt,
                sitemap_urls={"urls": result.sitemap_urls},
                meta=result.meta,
                favicon_url=result.favicon_url,
                nav_structure={"items": result.nav_structure},
                forms={"items": result.forms},
                buttons={"items": result.buttons},
                images={"items": result.images},
                fonts={"items": result.fonts},
                js_files={"items": result.js_files},
                css_files={"items": result.css_files},
                page_load_time_ms=result.page_load_time_ms,
                crawled_at=result.crawled_at,
            )
            screenshots = [
                Screenshot(device=DeviceType(shot.device), storage_path=shot.storage_path, width=shot.width, height=shot.height)
                for shot in result.screenshots
            ]
            await self._snapshots.create(snapshot, screenshots)

            await self._audit_jobs.log_event(
                audit_job_id=audit_job_id, stage=STAGE_NAME, status=JobEventStatus.SUCCEEDED,
                duration_ms=elapsed_ms(),
            )

        logger.info("crawl_stage_completed", audit_job_id=str(audit_job_id), final_url=result.final_url)
        return snapshot