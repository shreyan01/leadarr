from __future__ import annotations

import uuid

from app.ai.interfaces import VisionProvider
from app.core.exceptions import ProviderError
from app.core.logging import get_logger
from app.models.audit_job import JobEventStatus
from app.models.vision_analysis import VisionAnalysis
from app.repositories.audit_job_repository import AuditJobRepository
from app.repositories.finding_repository import VisionAnalysisRepository
from app.services.vision.vision_prompts import build_vision_prompt
from app.services.vision.vision_scoring import parse_vision_scores
from app.utils.stage_timer import stage_timer
from app.utils.storage import StorageBackend

logger = get_logger(__name__)

STAGE_NAME = "vision"

# Analyzing every viewport would multiply model calls for marginal signal;
# desktop carries the primary design judgment and mobile specifically
# grounds the mobile_friendliness score in what a phone visitor actually sees.
_DEVICES_TO_ANALYZE = ("desktop", "mobile")


class VisionStageService:
    def __init__(
        self,
        vision_provider: VisionProvider,
        storage: StorageBackend,
        analysis_repo: VisionAnalysisRepository,
        audit_job_repo: AuditJobRepository,
        model: str,
    ) -> None:
        self._vision = vision_provider
        self._storage = storage
        self._analyses = analysis_repo
        self._audit_jobs = audit_job_repo
        self._model = model

    async def run(self, *, audit_job_id: uuid.UUID, business_name: str, snapshot) -> list[VisionAnalysis]:
        await self._audit_jobs.mark_stage_started(audit_job_id, STAGE_NAME)

        targets = [s for s in snapshot.screenshots if s.device in _DEVICES_TO_ANALYZE]
        if not targets:
            await self._audit_jobs.log_event(
                audit_job_id=audit_job_id, stage=STAGE_NAME, status=JobEventStatus.FAILED,
                message="No desktop/mobile screenshots available to analyze.",
            )
            raise ProviderError("No screenshots available for vision analysis.")

        results: list[VisionAnalysis] = []
        with stage_timer() as elapsed_ms:
            total_input_tokens = 0
            total_output_tokens = 0
            try:
                for screenshot in targets:
                    analysis, input_tokens, output_tokens = await self._analyze_one(
                        audit_job_id, business_name, screenshot
                    )
                    results.append(await self._analyses.create(analysis))
                    total_input_tokens += input_tokens
                    total_output_tokens += output_tokens
            except Exception as exc:
                await self._audit_jobs.log_event(
                    audit_job_id=audit_job_id, stage=STAGE_NAME, status=JobEventStatus.FAILED,
                    duration_ms=elapsed_ms(), message=str(exc)[:1000],
                )
                raise

            await self._audit_jobs.log_event(
                audit_job_id=audit_job_id, stage=STAGE_NAME, status=JobEventStatus.SUCCEEDED,
                duration_ms=elapsed_ms(), model_used=self._model,
                tokens_input=total_input_tokens, tokens_output=total_output_tokens,
            )

        logger.info("vision_stage_completed", audit_job_id=str(audit_job_id), analyzed=len(results))
        return results

    async def _analyze_one(
        self, audit_job_id: uuid.UUID, business_name: str, screenshot
    ) -> tuple[VisionAnalysis, int, int]:
        image_bytes = await self._storage.read_bytes(screenshot.storage_path)
        prompt = build_vision_prompt(business_name=business_name, device=screenshot.device)

        result = await self._vision.analyze_image(image_bytes, prompt, model=self._model, media_type="image/png")
        scores = parse_vision_scores(result.structured)

        analysis = VisionAnalysis(
            audit_job_id=audit_job_id,
            screenshot_id=screenshot.id,
            provider="qwen_vl",
            model=result.model,
            raw_response=result.raw,
            **scores,
        )
        return analysis, result.input_tokens, result.output_tokens
