"""Auth API — 7 endpoints (all Phase 1-A)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import get_current_user
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    InviteAcceptRequest,
    InviteVerifyResponse,
    LoginRequest,
    LoginResponse,
    PasswordResetBody,
    PasswordResetRequestBody,
    RefreshRequest,
    RefreshResponse,
)
from app.schemas.common import ApiResponse
from app.services.auth_service import AuthService

router = APIRouter()


def _get_auth_service(db: AsyncSession = Depends(get_db_session)) -> AuthService:
    return AuthService(UserRepository(db))


# ── 1. POST /auth/login ─────────────────────────────────

@router.post("/login", response_model=ApiResponse[LoginResponse])
async def login(
    body: LoginRequest,
    service: AuthService = Depends(_get_auth_service),
) -> dict:
    result = await service.login(body.email, body.password, body.remember_me)
    return {"success": True, "data": result}


# ── 2. POST /auth/refresh ───────────────────────────────

@router.post("/refresh", response_model=ApiResponse[RefreshResponse])
async def refresh_token(
    body: RefreshRequest,
    service: AuthService = Depends(_get_auth_service),
) -> dict:
    result = await service.refresh(body.refresh_token)
    return {"success": True, "data": result}


# ── 3. POST /auth/logout ────────────────────────────────

@router.post("/logout", response_model=ApiResponse[None])
async def logout(
    body: RefreshRequest | None = None,
    user: User = Depends(get_current_user),
    service: AuthService = Depends(_get_auth_service),
) -> dict:
    await service.logout(str(user.id), body.refresh_token if body else None)
    return {"success": True, "data": None}


# ── 4. POST /auth/password/reset-request ─────────────────

@router.post("/password/reset-request", response_model=ApiResponse[None])
async def password_reset_request(
    body: PasswordResetRequestBody,
    service: AuthService = Depends(_get_auth_service),
) -> dict:
    from app.integrations.email import send_password_reset_email

    raw_token = await service.request_password_reset(body.email)
    if raw_token:
        await send_password_reset_email(body.email, raw_token)
    # Always return success (don't reveal email existence)
    return {"success": True, "data": None}


# ── 5. POST /auth/password/reset ─────────────────────────

@router.post("/password/reset", response_model=ApiResponse[None])
async def password_reset(
    body: PasswordResetBody,
    service: AuthService = Depends(_get_auth_service),
) -> dict:
    await service.reset_password(body)
    return {"success": True, "data": None}


# ── 6. POST /auth/invite/accept ─────────────────────────

@router.post("/invite/accept", response_model=ApiResponse[LoginResponse])
async def invite_accept(
    body: InviteAcceptRequest,
    service: AuthService = Depends(_get_auth_service),
) -> dict:
    result = await service.accept_invite(body)
    return {"success": True, "data": result}


# ── 7. GET /auth/invite/verify ───────────────────────────

@router.get("/invite/verify", response_model=ApiResponse[InviteVerifyResponse])
async def invite_verify(
    token: str = Query(...),
    service: AuthService = Depends(_get_auth_service),
) -> dict:
    result = await service.verify_invite(token)
    return {"success": True, "data": result}
