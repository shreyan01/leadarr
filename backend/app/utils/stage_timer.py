from __future__ import annotations

import time
from contextlib import contextmanager


@contextmanager
def stage_timer():
    """Yields a callable returning elapsed milliseconds so far; used to
    populate JobEvent.duration_ms uniformly across every pipeline stage."""
    start = time.monotonic()
    yield lambda: int((time.monotonic() - start) * 1000)
