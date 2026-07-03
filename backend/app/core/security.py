"""JWT issuing/verification, password hashing, and RBAC dependencies."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.config import Settings, get_settings

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class TokenPayload(BaseModel):
    sub: str  # user id
    org: str | None = None
    role: Role
    exp: datetime
    type: str  # "access" | "refresh"


def hash_password(raw_password: str) -> str:
    return _pwd_context.hash(raw_password)


def verify_password(raw_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(raw_password, hashed_password)


def _create_token(
    *, subject: uuid.UUID, role: Role, org_id: uuid.UUID | None,
    expires_delta: timedelta, token_type: str, settings: Settings,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "org": str(org_id) if org_id else None,
        "role": role.value,
        "exp": now + expires_delta,
        "iat": now,
        "type": token_type,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY.get_secret_value(), algorithm=settings.JWT_ALGORITHM)


def create_access_token(*, subject: uuid.UUID, role: Role, org_id: uuid.UUID | None, settings: Settings) -> str:
    return _create_token(
        subject=subject, role=role, org_id=org_id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access", settings=settings,
    )


def create_refresh_token(*, subject: uuid.UUID, role: Role, org_id: uuid.UUID | None, settings: Settings) -> str:
    return _create_token(
        subject=subject, role=role, org_id=org_id,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh", settings=settings,
    )


def decode_token(token: str, settings: Settings) -> TokenPayload:
    try:
        raw = jwt.decode(token, settings.JWT_SECRET_KEY.get_secret_value(), algorithms=[settings.JWT_ALGORITHM])
        return TokenPayload(**raw)
    except (JWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_token(
    token: str = Depends(oauth2_scheme),
    settings: Settings = Depends(get_settings),
) -> TokenPayload:
    payload = decode_token(token, settings)
    if payload.type != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    return payload


def require_role(*allowed: Role):
    """FastAPI dependency factory enforcing RBAC on a route."""

    def _checker(token: TokenPayload = Depends(get_current_token)) -> TokenPayload:
        if token.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return token

    return _checker
