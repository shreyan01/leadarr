"""Storage abstraction. Only a local-disk backend ships in this phase — the
interface is intentionally MinIO-shaped so swapping backends later (per
ARCHITECTURE.md's "MinIO (future)" note) doesn't touch any caller.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Protocol

from app.core.config import Settings, get_settings


class StorageBackend(Protocol):
    async def save_bytes(self, *, key: str, content: bytes) -> str: ...
    async def save_text(self, *, key: str, content: str) -> str: ...
    async def read_bytes(self, key: str) -> bytes: ...


class LocalStorageBackend:
    def __init__(self, root: str) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    async def save_bytes(self, *, key: str, content: bytes) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return str(path)

    async def save_text(self, *, key: str, content: str) -> str:
        return await self.save_bytes(key=key, content=content.encode("utf-8"))

    async def read_bytes(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    def _resolve(self, key: str) -> Path:
        # Defends against a crafted key escaping the storage root.
        candidate = (self._root / key).resolve()
        if self._root.resolve() not in candidate.parents and candidate != self._root.resolve():
            raise ValueError(f"Storage key escapes root: {key}")
        return candidate


def new_object_key(*, business_id: uuid.UUID, audit_job_id: uuid.UUID, kind: str, extension: str) -> str:
    """Builds a stable, collision-free storage key for one audit's artifact."""
    return f"{business_id}/{audit_job_id}/{kind}/{uuid.uuid4().hex}.{extension}"


def get_storage_backend(settings: Settings | None = None) -> StorageBackend:
    settings = settings or get_settings()
    if settings.STORAGE_BACKEND == "local":
        return LocalStorageBackend(settings.LOCAL_STORAGE_PATH)
    raise NotImplementedError(
        f"Storage backend '{settings.STORAGE_BACKEND}' not implemented yet — MinIO lands with Phase 9 hardening."
    )
