from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "leadforge",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks.discovery", "app.workers.tasks.crawl", "app.workers.tasks.audit"],
    # Phase 4+ appends accessibility, security_audit, vision, reporting, outreach modules
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="audit",
    task_routes={
        "app.workers.tasks.discovery.*": {"queue": "discovery"},
        "app.workers.tasks.crawl.*": {"queue": "crawl"},
        "app.workers.tasks.audit.*": {"queue": "audit"},
        "app.workers.tasks.reporting.*": {"queue": "reporting"},
        "app.workers.tasks.outreach.*": {"queue": "outreach"},
    },
)
