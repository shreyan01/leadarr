from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def liveness():
    return {"status": "ok"}


@router.get("/db")
async def database_health(session: AsyncSession = Depends(get_db)):
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}


@router.get("/queue")
async def queue_health(settings: Settings = Depends(get_settings)):
    client = Redis.from_url(settings.CELERY_BROKER_URL)
    try:
        depths = {
            queue: await client.llen(queue)
            for queue in ["discovery", "crawl", "audit", "reporting", "outreach"]
        }
    finally:
        await client.aclose()
    return {"queue_depths": depths}


@router.get("/workers")
async def worker_health():
    """Pings all Celery workers via the broker. Blocking call — offloaded
    to a thread so it doesn't stall the event loop."""
    from app.workers.celery_app import celery_app

    def _inspect() -> dict:
        inspector = celery_app.control.inspect(timeout=2.0)
        pings = inspector.ping() or {}
        active_counts = inspector.active() or {}
        return {
            "workers": [
                {"name": name, "status": "online", "active_tasks": len(active_counts.get(name, []))}
                for name in pings
            ],
            "worker_count": len(pings),
        }

    return await asyncio.to_thread(_inspect)
