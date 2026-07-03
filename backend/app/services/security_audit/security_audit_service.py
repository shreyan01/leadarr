"""Orchestrates the passive security-hygiene audit for one crawled site.

Every network read in this module goes through ``PassiveHttpClient``
(GET/HEAD only) or ``tls_inspector`` (a plain TLS handshake read). Checked
paths are either files a site conventionally exposes on purpose
(robots.txt, sitemap.xml, manifest) or well-known accidental-exposure
locations (.env, .git/config) — requesting them is exactly what a browser
or crawler does; nothing here submits data, guesses credentials, or acts on
a response beyond reading it.
"""
from __future__ import annotations

import uuid
from urllib.parse import urljoin, urlparse

from app.core.logging import get_logger
from app.models.audit_job import JobEventStatus
from app.models.security_finding import SecurityFinding
from app.repositories.audit_job_repository import AuditJobRepository
from app.repositories.finding_repository import SecurityFindingRepository
from app.services.security_audit import header_analyzer, secret_scanner
from app.services.security_audit.passive_http_client import PassiveHttpClient
from app.services.security_audit.tls_inspector import inspect_tls
from app.utils.stage_timer import stage_timer

logger = get_logger(__name__)

STAGE_NAME = "security_audit"

# Conventional locations where misconfigured servers accidentally expose
# secrets/config — checking whether a plain GET returns them is standard
# passive reconnaissance (the same thing a search-engine crawler would see).
_CONFIG_FILE_PATHS = [".env", ".git/config", "wp-config.php.bak", "config.json.bak", ".DS_Store", ".htaccess"]


class SecurityAuditStageService:
    def __init__(self, finding_repo: SecurityFindingRepository, audit_job_repo: AuditJobRepository) -> None:
        self._findings = finding_repo
        self._audit_jobs = audit_job_repo

    async def run(self, *, audit_job_id: uuid.UUID, snapshot) -> SecurityFinding:
        await self._audit_jobs.mark_stage_started(audit_job_id, STAGE_NAME)

        with stage_timer() as elapsed_ms:
            try:
                finding = await self._analyze(snapshot)
            except Exception as exc:
                await self._audit_jobs.log_event(
                    audit_job_id=audit_job_id, stage=STAGE_NAME, status=JobEventStatus.FAILED,
                    duration_ms=elapsed_ms(), message=str(exc)[:1000],
                )
                raise

            finding.audit_job_id = audit_job_id
            await self._findings.create(finding)
            await self._audit_jobs.log_event(
                audit_job_id=audit_job_id, stage=STAGE_NAME, status=JobEventStatus.SUCCEEDED,
                duration_ms=elapsed_ms(),
            )

        logger.info("security_audit_completed", audit_job_id=str(audit_job_id), hygiene_score=finding.hygiene_score)
        return finding

    async def _analyze(self, snapshot) -> SecurityFinding:
        client = PassiveHttpClient()
        try:
            homepage = await client.get(snapshot.final_url)
            parsed = urlparse(snapshot.final_url)
            hostname = parsed.hostname

            tls_info = inspect_tls(hostname) if parsed.scheme == "https" and hostname else None

            set_cookie_values = (
                homepage.headers.get_list("set-cookie") if hasattr(homepage.headers, "get_list") else []
            )
            header_findings = header_analyzer.analyze_headers(dict(homepage.headers), set_cookie_values)

            mixed_content = header_analyzer.detect_mixed_content(
                homepage.text, page_is_https=(parsed.scheme == "https")
            )

            js_files = (snapshot.js_files or {}).get("items", [])
            css_files = (snapshot.css_files or {}).get("items", [])

            exposed_config_files = await self._check_config_files(client, snapshot.final_url)
            exposed_source_maps = await self._check_source_maps(client, js_files)
            directory_listing_exposed = await self._check_directory_listing(client, js_files + css_files)

            secrets_found: list[dict] = []
            api_endpoints: set[str] = set()
            for js_url in js_files[:15]:  # cap fetch volume per audit
                try:
                    js_response = await client.get(js_url)
                    secrets_found.extend(secret_scanner.scan_for_secrets(js_response.text, source=js_url))
                    api_endpoints.update(secret_scanner.scan_for_public_api_endpoints(js_response.text))
                except Exception:  # noqa: BLE001 — one bad asset shouldn't fail the whole audit
                    continue

            manifest_present = await self._path_exists(
                client, snapshot.final_url, "/site.webmanifest"
            ) or await self._path_exists(client, snapshot.final_url, "/manifest.json")
            service_worker_present = "serviceworker" in homepage.text.lower() or "sw.js" in homepage.text.lower()

            hygiene_score = header_analyzer.compute_hygiene_score(
                https=(parsed.scheme == "https"),
                header_findings=header_findings,
                mixed_content=mixed_content,
                directory_listing_exposed=directory_listing_exposed,
                exposed_source_maps_count=len(exposed_source_maps),
                exposed_config_files_count=len(exposed_config_files),
                exposed_secrets_count=len(secrets_found),
            )

            return SecurityFinding(
                https=(parsed.scheme == "https"),
                tls_version=tls_info.tls_version if tls_info else None,
                cert_issuer=tls_info.cert_issuer if tls_info else None,
                cert_expires_at=tls_info.cert_expires_at if tls_info else None,
                hsts=header_findings.hsts,
                csp=header_findings.csp,
                permissions_policy=header_findings.permissions_policy,
                referrer_policy=header_findings.referrer_policy,
                x_frame_options=header_findings.x_frame_options,
                x_content_type_options=header_findings.x_content_type_options,
                cookie_flags={"cookies": header_findings.cookie_flags},
                mixed_content=mixed_content,
                directory_listing_exposed=directory_listing_exposed,
                exposed_source_maps={"urls": exposed_source_maps},
                exposed_config_files={"paths": exposed_config_files},
                exposed_secrets_regex_hits={"findings": secrets_found},
                tech_fingerprint={},  # populated from validation-stage detection; joined at report time
                server_header=header_findings.server_header,
                compression=header_findings.compression,
                caching_headers=header_findings.caching_headers,
                public_api_endpoints={"endpoints": sorted(api_endpoints)},
                manifest_present=manifest_present,
                service_worker_present=service_worker_present,
                hygiene_score=hygiene_score,
            )
        finally:
            await client.aclose()

    @staticmethod
    async def _check_config_files(client: PassiveHttpClient, base_url: str) -> list[str]:
        found = []
        for path in _CONFIG_FILE_PATHS:
            try:
                response = await client.get(urljoin(base_url, path))
                if response.status_code == 200 and "text/html" not in response.headers.get("content-type", ""):
                    found.append(path)
            except Exception:  # noqa: BLE001
                continue
        return found

    @staticmethod
    async def _check_source_maps(client: PassiveHttpClient, js_files: list[str]) -> list[str]:
        found = []
        for js_url in js_files[:15]:
            map_url = f"{js_url}.map"
            try:
                response = await client.head(map_url)
                if response.status_code == 200:
                    found.append(map_url)
            except Exception:  # noqa: BLE001
                continue
        return found

    @staticmethod
    async def _check_directory_listing(client: PassiveHttpClient, asset_urls: list[str]) -> bool:
        parents = {u.rsplit("/", 1)[0] + "/" for u in asset_urls if "/" in u}
        for directory_url in list(parents)[:10]:
            try:
                response = await client.get(directory_url)
                if response.status_code == 200 and "index of /" in response.text.lower():
                    return True
            except Exception:  # noqa: BLE001
                continue
        return False

    @staticmethod
    async def _path_exists(client: PassiveHttpClient, base_url: str, path: str) -> bool:
        try:
            response = await client.head(urljoin(base_url, path))
            return response.status_code == 200
        except Exception:  # noqa: BLE001
            return False
