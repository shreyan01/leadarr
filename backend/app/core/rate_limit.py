"""Redis-backed fixed-window rate limiting.

Applied via FastAPI dependency on auth and audit-trigger endpoints per
ARCHITECTURE.md §6. Keyed by client IP for unauthenticated endpoints
(login/register) and by user id for authenticated ones, so one abusive
client can't exhaust another's quota.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis

from app.core.config import Settings, get_settings

_redis_client: Redis | None = None


def _get_redis(settings: Settings) -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(str(settings.REDIS_URL))
    return _redis_client


class RateLimiter:
    """Fixed 60-second window counter. Simple and predictable — an agency's
    own dashboard traffic is bursty but low-volume, so a fixed window is
    plenty; a sliding-window/token-bucket refinement is a drop-in swap here
    if usage patterns ever demand it."""

    def __init__(self, *, limit: int | None = None, scope: str = "default") -> None:
        self._limit = limit
        self._scope = scope

    async def __call__(self, request: Request, settings: Settings = Depends(get_settings)) -> None:
        limit = self._limit or settings.RATE_LIMIT_PER_MINUTE
        identity = _client_identity(request)
        key = f"ratelimit:{self._scope}:{identity}"

        redis = _get_redis(settings)
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 60)

        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please slow down and try again shortly.",
            )


def _client_identity(request: Request) -> str:
    auth_header = request.headers.get("authorization")
    if auth_header:
        # Coarse but sufficient: distinct tokens get distinct buckets without
        # needing to decode the JWT just for rate limiting.
        return f"token:{hash(auth_header) % 10_000_000}"
    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


# Pre-built dependency instances for the endpoints that need stricter limits
# than the global default (brute-force protection on auth in particular).
auth_rate_limiter = RateLimiter(limit=10, scope="auth")
audit_trigger_rate_limiter = RateLimiter(limit=20, scope="audit_trigger")
default_rate_limiter = RateLimiter(scope="default")
