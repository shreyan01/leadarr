"""Runs a single coroutine to completion inside its own event loop, then
disposes the shared async engine's connection pool before that loop closes.

Celery's prefork workers call `asyncio.run()` once per task — a brand new
event loop is created and destroyed on every single task invocation.
SQLAlchemy's async engine (``app.db.session.engine``) is a single
module-level object whose connection pool holds real asyncpg connections
tied to whichever event loop was running when they were opened. If a
pooled connection survives from one task's ``asyncio.run()`` call into the
next task's, any operation on it — including just closing it — crashes
with "Event loop is closed" or "attached to a different loop", since the
loop it was born on is long gone.

Disposing the pool here, while still inside the same loop that used it,
guarantees the next task starts with an empty pool and opens fresh
connections instead of touching a stale one. Every Celery task's
``asyncio.run(...)`` call should go through this helper instead of calling
``asyncio.run`` directly.
"""
from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import TypeVar

from app.db.session import engine

T = TypeVar("T")


def run_worker_task(coro: Coroutine[None, None, T]) -> T:
    async def _run_and_dispose() -> T:
        try:
            return await coro
        finally:
            await engine.dispose()

    return asyncio.run(_run_and_dispose())