from __future__ import annotations

import uuid

from app.adapters.lighthouse_cli import LighthouseCliAdapter, parse_lighthouse_report
from app.core.logging import get_logger
from app.models.audit_job import JobEventStatus
from app.models.lighthouse_report import LighthouseReport
from app.repositories.audit_artifacts_repository import LighthouseReportRepository
from app.repositories.audit_job_repository import AuditJobRepository
from app.utils.stage_timer import stage_timer
from app.utils.storage import StorageBackend, new_object_key

logger = get_logger(__name__)

STAGE_NAME = "lighthouse"


class LighthouseStageService:
    def __init__(
        self,
        cli: LighthouseCliAdapter,
        storage: StorageBackend,
        report_repo: LighthouseReportRepository,
        audit_job_repo: AuditJobRepository,
    ) -> None:
        self._cli = cli
        self._storage = storage
        self._reports = report_repo
        self._audit_jobs = audit_job_repo

    async def run(self, *, audit_job_id: uuid.UUID, business_id: uuid.UUID, url: str) -> LighthouseReport:
        await self._audit_jobs.mark_stage_started(audit_job_id, STAGE_NAME)

        with stage_timer() as elapsed_ms:
            try:
                raw = await self._cli.run(url)
            except Exception as exc:
                await self._audit_jobs.log_event(
                    audit_job_id=audit_job_id, stage=STAGE_NAME, status=JobEventStatus.FAILED,
                    duration_ms=elapsed_ms(), message=str(exc)[:1000],
                )
                raise

            key = new_object_key(business_id=business_id, audit_job_id=audit_job_id, kind="lighthouse", extension="json")
            import json

            raw_path = await self._storage.save_text(key=key, content=json.dumps(raw))

            parsed = parse_lighthouse_report(raw)
            report = LighthouseReport(audit_job_id=audit_job_id, raw_json_storage_path=raw_path, **parsed)
            await self._reports.create(report)

            await self._audit_jobs.log_event(
                audit_job_id=audit_job_id, stage=STAGE_NAME, status=JobEventStatus.SUCCEEDED, duration_ms=elapsed_ms(),
            )

        logger.info("lighthouse_stage_completed", audit_job_id=str(audit_job_id), scores=parsed)
        return report
