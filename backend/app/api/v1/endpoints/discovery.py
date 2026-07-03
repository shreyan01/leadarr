from __future__ import annotations

from celery.result import AsyncResult
from fastapi import APIRouter, Depends

from app.core.security import Role, TokenPayload, require_role
from app.core.rate_limit import audit_trigger_rate_limiter
from app.schemas.business import DiscoveryJobAccepted, DiscoveryJobStatus, DiscoveryRequest
from app.workers.celery_app import celery_app
from app.workers.tasks.discovery import run_discovery

router = APIRouter(prefix="/discovery", tags=["discovery"])


@router.post("/search", response_model=DiscoveryJobAccepted, status_code=202, dependencies=[Depends(audit_trigger_rate_limiter)])
async def start_discovery(
    payload: DiscoveryRequest,
    token: TokenPayload = Depends(require_role(Role.OWNER, Role.ADMIN, Role.ANALYST)),
):
    async_result = run_discovery.delay(
        organization_id=token.org,
        country=payload.country,
        city=payload.city,
        category=payload.category,
        limit=payload.limit,
    )
    return DiscoveryJobAccepted(task_id=async_result.id)


@router.get("/jobs/{task_id}", response_model=DiscoveryJobStatus)
async def get_discovery_job(task_id: str):
    result = AsyncResult(task_id, app=celery_app)

    if result.state == "PENDING":
        return DiscoveryJobStatus(task_id=task_id, status="pending")
    if result.state == "STARTED":
        return DiscoveryJobStatus(task_id=task_id, status="running")
    if result.state == "SUCCESS":
        return DiscoveryJobStatus(
            task_id=task_id, status="completed", discovered_count=result.result.get("discovered_count")
        )
    if result.state == "FAILURE":
        return DiscoveryJobStatus(task_id=task_id, status="failed", error=str(result.info))
    return DiscoveryJobStatus(task_id=task_id, status=result.state.lower())
