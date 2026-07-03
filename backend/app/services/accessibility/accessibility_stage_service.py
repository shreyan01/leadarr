from __future__ import annotations

import uuid

from app.core.logging import get_logger
from app.models.accessibility_finding import AccessibilityFinding
from app.models.audit_job import JobEventStatus
from app.repositories.audit_job_repository import AuditJobRepository
from app.repositories.finding_repository import AccessibilityFindingRepository
from app.services.accessibility import accessibility_analyzer as analyzer
from app.services.crawl import html_parser
from app.utils.stage_timer import stage_timer
from app.utils.storage import StorageBackend

logger = get_logger(__name__)

STAGE_NAME = "accessibility"


class AccessibilityStageService:
    def __init__(
        self, storage: StorageBackend, finding_repo: AccessibilityFindingRepository, audit_job_repo: AuditJobRepository
    ) -> None:
        self._storage = storage
        self._findings = finding_repo
        self._audit_jobs = audit_job_repo

    async def run(self, *, audit_job_id: uuid.UUID, snapshot) -> AccessibilityFinding:
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
                audit_job_id=audit_job_id, stage=STAGE_NAME, status=JobEventStatus.SUCCEEDED,
                duration_ms=elapsed_ms(),
            )

        logger.info("accessibility_stage_completed", audit_job_id=str(audit_job_id), score=finding.accessibility_score)
        return finding

    async def _analyze(self, audit_job_id: uuid.UUID, snapshot) -> AccessibilityFinding:
        html_bytes = await self._storage.read_bytes(snapshot.html_storage_path)
        html = html_bytes.decode("utf-8", errors="replace")

        headings = html_parser.extract_headings(html)
        color_pairs = html_parser.extract_inline_color_pairs(html)
        clickable_issues = html_parser.extract_clickable_non_interactive_elements(html)

        images = (snapshot.images or {}).get("items", [])
        forms = (snapshot.forms or {}).get("items", [])
        buttons = (snapshot.buttons or {}).get("items", [])

        missing_alt_count, missing_alt_items = analyzer.compute_missing_alt(images)
        heading_issues = analyzer.compute_heading_hierarchy_issues(headings)
        unlabeled_buttons = analyzer.compute_unlabeled_buttons(buttons)
        unlabeled_fields = analyzer.compute_unlabeled_form_fields(forms)
        contrast_issues = analyzer.compute_contrast_issues(color_pairs)
        keyboard_nav_issues = analyzer.compute_keyboard_nav_issues(clickable_issues)

        score = analyzer.compute_accessibility_score(
            missing_alt_count=missing_alt_count,
            heading_issues_count=len(heading_issues),
            contrast_issues_count=len(contrast_issues),
            unlabeled_buttons_count=len(unlabeled_buttons),
            unlabeled_fields_count=len(unlabeled_fields),
            keyboard_nav_issues_count=len(keyboard_nav_issues),
        )

        return AccessibilityFinding(
            audit_job_id=audit_job_id,
            missing_alt_count=missing_alt_count,
            heading_hierarchy_issues={"issues": heading_issues},
            aria_issues={"issues": []},  # requires rendered ARIA tree; deferred to Phase 5 vision pass
            contrast_issues={"issues": contrast_issues},
            unlabeled_buttons={"items": unlabeled_buttons},
            keyboard_nav_issues={"items": keyboard_nav_issues},
            unlabeled_form_fields={"items": unlabeled_fields},
            accessibility_score=score,
        )
