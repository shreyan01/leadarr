from __future__ import annotations

import uuid

from app.core.config import Settings
from app.core.exceptions import ConflictError, ValidationError
from app.core.security import (
    Role,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, user_repo: UserRepository, settings: Settings) -> None:
        self._users = user_repo
        self._settings = settings

    async def register(self, *, organization_name: str, full_name: str, email: str, password: str):
        existing = await self._users.get_by_email(email)
        if existing is not None:
            raise ConflictError("An account with this email already exists.")

        user = await self._users.create_with_organization(
            organization_name=organization_name,
            full_name=full_name,
            email=email,
            hashed_password=hash_password(password),
        )
        return self._issue_tokens(user)

    async def login(self, *, email: str, password: str):
        user = await self._users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise ValidationError("Invalid email or password.")
        if not user.is_active:
            raise ValidationError("This account has been deactivated.")
        return self._issue_tokens(user)

    async def refresh(self, *, refresh_token: str):
        payload = decode_token(refresh_token, self._settings)
        if payload.type != "refresh":
            raise ValidationError("Invalid refresh token.")
        user = await self._users.get_by_id(uuid.UUID(payload.sub))
        if user is None or not user.is_active:
            raise ValidationError("Invalid refresh token.")
        return self._issue_tokens(user)

    def _issue_tokens(self, user) -> dict[str, str]:
        role = Role(user.role.value)
        access = create_access_token(
            subject=user.id, role=role, org_id=user.organization_id, settings=self._settings
        )
        refresh = create_refresh_token(
            subject=user.id, role=role, org_id=user.organization_id, settings=self._settings
        )
        return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}
