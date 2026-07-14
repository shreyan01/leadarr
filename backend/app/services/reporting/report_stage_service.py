from __future__ import annotations

import uuid

from app.ai.interfaces import ChatProvider, Message
from app.core.logging import get_logger
from app.models.ai_report import AIReport
from app.models.audit_job import JobEventStatus
from app.repositories.ai_report_repository import AIReportRepository
from app.repositories.audit_job_repository import AuditJobRepository
from app.services.reporting.markdown_renderer import render_html, render_markdown
from app.services.reporting.report_parser import parse_report_response
from app.services.reporting.report_prompts import ReportInputs, build_report_prompt
from app.utils.stage_timer import stage_timer
from app.utils.storage import StorageBackend, new_object_key

logger = get_logger(__name__)

STAGE_NAME = "reporting"


class ReportStageService:
    def __init__(
        self,
        chat_provider: ChatProvider,
        storage: StorageBackend,
        report_repo: AIReportRepository,
        audit_job_repo: AuditJobRepository,
        model: str,
        provider_name: str,
    ) -> None:
        self._chat = chat_provider
        self._storage = storage
        self._reports = report_repo
        self._audit_jobs = audit_job_repo
        self._model = model
        self._provider_name = provider_name

    async def run(
        self,
        *,
        audit_job_id: uuid.UUID,
        business_id: uuid.UUID,
        report_inputs: ReportInputs,
        lead_score: float | None,
        priority: str | None,
    ) -> AIReport:
        await self._audit_jobs.mark_stage_started(audit_job_id, STAGE_NAME)

        with stage_timer() as elapsed_ms:
            try:
                prompt = build_report_prompt(report_inputs)
                result = await self._chat.complete(
                    [Message(role="user", content=prompt)], model=self._model, temperature=0.3, max_tokens=3000
                )
                parsed = parse_report_response(result.text)

                markdown_text = render_markdown(
                    business_name=report_inputs.business_name,
                    report=parsed,
                    lead_score=lead_score,
                    priority=priority,
                )
                html_text = render_html(markdown_text)

                md_key = new_object_key(business_id=business_id, audit_job_id=audit_job_id, kind="report", extension="md")
                html_key = new_object_key(
                    business_id=business_id, audit_job_id=audit_job_id, kind="report", extension="html"
                )
                md_path = await self._storage.save_text(key=md_key, content=markdown_text)
                html_path = await self._storage.save_text(key=html_key, content=html_text)

            except Exception as exc:
                await self._audit_jobs.log_event(
                    audit_job_id=audit_job_id, stage=STAGE_NAME, status=JobEventStatus.FAILED,
                    duration_ms=elapsed_ms(), message=str(exc)[:1000],
                )
                raise

            report = AIReport(
                audit_job_id=audit_job_id,
                provider=self._provider_name,
                model=result.model,
                executive_summary=parsed["executive_summary"],
                technical_summary=parsed["technical_summary"],
                business_summary=parsed["business_summary"],
                seo_summary=parsed["seo_summary"],
                accessibility_summary=parsed["accessibility_summary"],
                security_summary=parsed["security_summary"],
                design_summary=parsed["design_summary"],
                top_improvements={"items": parsed["top_improvements"]},
                estimated_effort=parsed["estimated_effort"],
                priority_fixes={"items": parsed["priority_fixes"]},
                estimated_business_impact=parsed["estimated_business_impact"],
                markdown_storage_path=md_path,
                html_storage_path=html_path,
            )
            await self._reports.create(report)

            await self._audit_jobs.log_event(
                audit_job_id=audit_job_id, stage=STAGE_NAME, status=JobEventStatus.SUCCEEDED,
                duration_ms=elapsed_ms(), model_used=result.model,
                tokens_input=result.input_tokens, tokens_output=result.output_tokens,
            )

        logger.info("report_stage_completed", audit_job_id=str(audit_job_id))
        return report