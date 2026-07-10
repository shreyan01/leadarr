"""Crawl orchestration — the only module that touches Playwright directly.

Fetches robots.txt/sitemap.xml via a plain httpx GET (reading files a site
publishes for exactly this purpose), renders the homepage in a real browser
to get post-JS HTML, captures desktop/tablet/mobile screenshots, and hands
the HTML off to ``html_parser`` for structured extraction. No interaction
beyond navigation — no form submission, no clicking, nothing that acts on
the target rather than reads it.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app.core.config import Settings
from app.core.logging import get_logger
from app.services.crawl import html_parser
from app.utils.storage import StorageBackend, new_object_key

logger = get_logger(__name__)

_VIEWPORTS = {
    "desktop": {"width": 1440, "height": 900},
    "tablet": {"width": 768, "height": 1024},
    "mobile": {"width": 390, "height": 844},
}


@dataclass
class ScreenshotArtifact:
    device: str
    storage_path: str
    width: int
    height: int


@dataclass
class CrawlResult:
    final_url: str
    http_status: int
    redirect_chain: list[str]
    html_storage_path: str
    robots_txt: str | None
    sitemap_urls: list[str]
    meta: dict
    favicon_url: str | None
    nav_structure: list[dict]
    forms: list[dict]
    buttons: list[dict]
    images: list[dict]
    fonts: list[str]
    js_files: list[str]
    css_files: list[str]
    page_load_time_ms: float
    screenshots: list[ScreenshotArtifact] = field(default_factory=list)
    crawled_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CrawlerService:
    def __init__(self, storage: StorageBackend, settings: Settings) -> None:
        self._storage = storage
        self._settings = settings

    async def crawl(self, *, url: str, business_id: uuid.UUID, audit_job_id: uuid.UUID) -> CrawlResult:
        robots_txt = await self._fetch_optional_text(self._join(url, "/robots.txt"))
        sitemap_xml = await self._fetch_optional_text(self._join(url, "/sitemap.xml"))
        sitemap_urls = html_parser.parse_sitemap_urls(sitemap_xml) if sitemap_xml else []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self._settings.PLAYWRIGHT_HEADLESS)
            try:
                page = await browser.new_page(viewport=_VIEWPORTS["desktop"])
                nav_start = time.monotonic()
                # "load" rather than "networkidle": plenty of real sites
                # (chat widgets, analytics beacons, ad trackers that poll
                # forever) never go fully network-idle, which turned a
                # normal page load into a spurious 30s timeout failure.
                # "load" only waits for the page's own load event, not for
                # background requests to stop entirely.
                try:
                    response = await page.goto(url, wait_until="load", timeout=45_000)
                except PlaywrightTimeoutError:
                    # Even "load" can time out on a handful of genuinely slow
                    # or broken sites. Rather than fail the whole audit, fall
                    # back to whatever rendered so far — a partial crawl of a
                    # slow site is more useful than no audit at all.
                    response = None
                page_load_time_ms = (time.monotonic() - nav_start) * 1000
                final_url = page.url
                http_status = response.status if response else 0
                redirect_chain = self._build_redirect_chain(response, final_url)
                html = await page.content()

                screenshots = [await self._capture(page, business_id, audit_job_id, "desktop")]
                for device in ("tablet", "mobile"):
                    await page.set_viewport_size(_VIEWPORTS[device])
                    screenshots.append(await self._capture(page, business_id, audit_job_id, device))
            finally:
                await browser.close()

        html_key = new_object_key(business_id=business_id, audit_job_id=audit_job_id, kind="html", extension="html")
        html_storage_path = await self._storage.save_text(key=html_key, content=html)

        meta = html_parser.extract_metadata(html, final_url)

        return CrawlResult(
            final_url=final_url,
            http_status=http_status,
            redirect_chain=redirect_chain,
            html_storage_path=html_storage_path,
            robots_txt=robots_txt,
            sitemap_urls=sitemap_urls,
            meta=meta,
            favicon_url=html_parser.extract_favicon(html, final_url),
            nav_structure=html_parser.extract_nav_structure(html, final_url),
            forms=html_parser.extract_forms(html),
            buttons=html_parser.extract_buttons(html),
            images=html_parser.extract_images(html, final_url),
            fonts=html_parser.extract_fonts(html, final_url),
            js_files=html_parser.extract_js_files(html, final_url),
            css_files=html_parser.extract_css_files(html, final_url),
            page_load_time_ms=page_load_time_ms,
            screenshots=screenshots,
        )

    async def _capture(self, page, business_id: uuid.UUID, audit_job_id: uuid.UUID, device: str) -> ScreenshotArtifact:
        # Viewport-only, not full-page: a full-page capture can be
        # arbitrarily tall for a long homepage, which produces far more
        # vision tokens than the model's context budget allows (vLLM
        # rejects an oversized multimodal request with a 400). It's also
        # the more correct choice for what we're actually scoring — trust,
        # professionalism, and design first-impressions are naturally
        # formed from what's visible without scrolling.
        png_bytes = await page.screenshot(full_page=False)
        key = new_object_key(business_id=business_id, audit_job_id=audit_job_id, kind=f"screenshot_{device}", extension="png")
        path = await self._storage.save_bytes(key=key, content=png_bytes)
        viewport = _VIEWPORTS[device]
        return ScreenshotArtifact(device=device, storage_path=path, width=viewport["width"], height=viewport["height"])

    @staticmethod
    def _build_redirect_chain(response, final_url: str) -> list[str]:
        if response is None:
            return [final_url]
        requests = []
        current_request = response.request
        while current_request is not None:
            requests.append(current_request)
            current_request = current_request.redirected_from
        requests.reverse()
        chain = [r.url for r in requests]
        if not chain or chain[-1] != final_url:
            chain.append(final_url)
        return chain

    @staticmethod
    def _join(base_url: str, path: str) -> str:
        from urllib.parse import urljoin

        return urljoin(base_url, path)

    @staticmethod
    async def _fetch_optional_text(url: str) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.text
        except httpx.HTTPError as exc:
            logger.info("optional_fetch_failed", url=url, error=str(exc))
        return None