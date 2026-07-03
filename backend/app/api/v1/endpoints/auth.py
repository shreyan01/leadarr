from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.di import get_auth_service, get_user_repository
from app.core.exceptions import NotFoundError
from app.core.rate_limit import auth_rate_limiter
from app.core.security import TokenPayload, get_current_token
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserOut
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201, dependencies=[Depends(auth_rate_limiter)])
async def register(payload: RegisterRequest, auth_service: AuthService = Depends(get_auth_service)):
    tokens = await auth_service.register(
        organization_name=payload.organization_name,
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
    )
    return TokenResponse(**tokens)


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(auth_rate_limiter)])
async def login(payload: LoginRequest, auth_service: AuthService = Depends(get_auth_service)):
    tokens = await auth_service.login(email=payload.email, password=payload.password)
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, auth_service: AuthService = Depends(get_auth_service)):
    tokens = await auth_service.refresh(refresh_token=payload.refresh_token)
    return TokenResponse(**tokens)


@router.get("/me", response_model=UserOut)
async def me(
    token: TokenPayload = Depends(get_current_token),
    user_repo: UserRepository = Depends(get_user_repository),
):
    import uuid

    user = await user_repo.get_by_id(uuid.UUID(token.sub))
    if user is None:
        raise NotFoundError("User not found.")
    return user
