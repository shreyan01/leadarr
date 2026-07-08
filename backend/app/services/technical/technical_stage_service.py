from __future__ import annotations

import uuid

from app.core.logging import get_logger
from app.models.audit_job import JobEventStatus
from app.models.technical_finding import TechnicalFinding
from app.repositories.audit_job_repository import AuditJobRepository
from app.repositories.technical_finding_repository import TechnicalFindingRepository
from app.services.crawl import html_parser
from app.services.security_audit.passive_http_client import PassiveHttpClient
from app.services.technical import technical_analyzer as analyzer
from app.services.technical.image_analyzer import analyze_image
from app.services.technical.link_checker import check_broken_links
from app.utils.stage_timer import stage_timer
from app.utils.storage import StorageBackend

logger = get_logger(__name__)

STAGE_NAME = "technical_audit"

# Caps on how much a single audit fetches — this is a hygiene/SEO check,
# not an exhaustive site crawl, so it stays bounded regardless of site size.
_MAX_IMAGES_CHECKED = 15


class TechnicalAuditStageService:
    def __init__(
        self, storage: StorageBackend, finding_repo: TechnicalFindingRepository, audit_job_repo: AuditJobRepository
    ) -> None:
        self._storage = storage
        self._findings = finding_repo
        self._audit_jobs = audit_job_repo

    async def run(self, *, audit_job_id: uuid.UUID, snapshot) -> TechnicalFinding:
        await self._audit_jobs.mark_stage_started(audit_job_id, STAGE_NAME)

        with stage_timer() as elapsed_ms:
            try:
                finding = await self._analyze(audit_job_id, snapshot)
            except Exception as exc:
                await self._audit_jobs.log_event(
                    audit_job_id=audit_job_id, stage=STAGE_NAME, status=JobEventStatus.FAILED,
                    duration_ms=elapsed_ms(), message=str(exc)[:1000],
                )
                raise

            await self._findings.create(finding)
            await self._audit_jobs.log_event(
                audit_job_id=audit_job_id, stage=STAGE_NAME, status=JobEventStatus.SUCCEEDED, duration_ms=elapsed_ms(),
            )

        logger.info("technical_audit_completed", audit_job_id=str(audit_job_id), score=finding.technical_score)
        return finding

    async def _analyze(self, audit_job_id: uuid.UUID, snapshot) -> TechnicalFinding:
        html_bytes = await self._storage.read_bytes(snapshot.html_storage_path)
        html = html_bytes.decode("utf-8", errors="replace")

        meta = snapshot.meta or {}
        open_graph = meta.get("open_graph") or {}
        twitter_card = meta.get("twitter_card") or {}
        structured_data = meta.get("structured_data") or []

        sitemap_present = analyzer.check_sitemap_present((snapshot.sitemap_urls or {}).get("urls", []))
        robots_present = analyzer.check_robots_present(snapshot.robots_txt)
        favicon_present = bool(snapshot.favicon_url)
        schema_present, schema_valid = analyzer.check_schema_markup(structured_data)
        og_present, twitter_present = analyzer.check_social_metadata(open_graph, twitter_card)
        google_business_link = html_parser.detect_google_business_link(html)

        client = PassiveHttpClient()
        try:
            links = html_parser.extract_all_links(html, snapshot.final_url)
            broken_links = await check_broken_links(client, links)

            image_urls = [img["src"] for img in (snapshot.images or {}).get("items", [])][:_MAX_IMAGES_CHECKED]
            oversized_images = []
            for image_url in image_urls:
                try:
                    response = await client.get(image_url)
                    result = analyze_image(response.content, url=image_url)
                    if result.is_oversized:
                        oversized_images.append(
                            {"url": result.url, "size_bytes": result.size_bytes, "reason": result.reason}
                        )
                except Exception:  # noqa: BLE001 — one broken image fetch shouldn't fail the whole audit
                    continue
        finally:
            await client.aclose()

        score = analyzer.compute_technical_score(
            sitemap_present=sitemap_present,
            robots_present=robots_present,
            favicon_present=favicon_present,
            schema_present=schema_present,
            schema_valid=schema_valid,
            open_graph_present=og_present,
            broken_links_count=len(broken_links),
            oversized_images_count=len(oversized_images),
        )

        return TechnicalFinding(
            audit_job_id=audit_job_id,
            page_load_time_ms=snapshot.page_load_time_ms,
            sitemap_present=sitemap_present,
            robots_present=robots_present,
            favicon_present=favicon_present,
            schema_markup_present=schema_present,
            schema_markup_valid=schema_valid,
            open_graph_present=og_present,
            twitter_card_present=twitter_present,
            google_business_link=google_business_link,
            broken_links={"items": broken_links},
            broken_links_count=len(broken_links),
            oversized_images={"items": oversized_images},
            oversized_images_count=len(oversized_images),
            technical_score=score,
        )