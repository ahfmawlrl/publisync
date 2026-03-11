"""Users API — 7 endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import get_current_user, require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.org_repository import OrgRepository
from app.repositories.user_repository import UserRepository
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta
from app.schemas.user import (
    RoleResponse,
    UserCreateRequest,
    UserMeResponse,
    UserResponse,
    UserUpdateRequest,
)
from app.services.org_service import OrgService
from app.services.user_service import UserService

router = APIRouter()
roles_router = APIRouter()


def _get_user_service(db: AsyncSession = Depends(get_db_session)) -> UserService:
    return UserService(UserRepository(db))


def _get_org_service(db: AsyncSession = Depends(get_db_session)) -> OrgService:
    return OrgService(OrgRepository(db))


def _to_user_response(u: User) -> UserResponse:
    return UserResponse(
        id=str(u.id),
        email=u.email,
        name=u.name,
        role=u.role.value,
        status=u.status.value,
        organization_id=str(u.organization_id) if u.organization_id else None,
        profile_image_url=u.profile_image_url,
        last_login_at=u.last_login_at.isoformat() if u.last_login_at else None,
        created_at=u.created_at.isoformat(),
    )


# ── GET /users/me ────────────────────────────────────────

@router.get("/me", response_model=ApiResponse[UserMeResponse])
async def get_me(
    user: User = Depends(get_current_user),
    service: UserService = Depends(_get_user_service),
) -> dict:
    data = await service.get_me(user)
    return {"success": True, "data": data}


# ── GET /users ───────────────────────────────────────────

@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    role: UserRole | None = None,
    status: str | None = Query(None),
    organization_id: UUID | None = None,
    _user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN, UserRole.AGENCY_MANAGER)),
    service: UserService = Depends(_get_user_service),
) -> dict:
    users, total = await service.list_users(
        org_id=organization_id, role=role, search=search, status=status, page=page, limit=limit,
    )
    return {
        "success": True,
        "data": [_to_user_response(u) for u in users],
        "meta": PaginationMeta(
            total=total,
            page=page,
            limit=limit,
            total_pages=(total + limit - 1) // limit,
        ),
    }


# ── POST /users ──────────────────────────────────────────

@router.post("", response_model=ApiResponse[UserResponse], status_code=201)
async def create_user(
    body: UserCreateRequest,
    _user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN, UserRole.AGENCY_MANAGER)),
    service: UserService = Depends(_get_user_service),
) -> dict:
    user = await service.create_user(body)
    return {"success": True, "data": _to_user_response(user)}


# ── GET /users/:id ───────────────────────────────────────

@router.get("/{user_id}", response_model=ApiResponse[UserResponse])
async def get_user(
    user_id: UUID,
    _user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN, UserRole.AGENCY_MANAGER)),
    service: UserService = Depends(_get_user_service),
) -> dict:
    user = await service.get_user(user_id)
    return {"success": True, "data": _to_user_response(user)}


# ── PUT /users/:id ───────────────────────────────────────

@router.put("/{user_id}", response_model=ApiResponse[UserResponse])
async def update_user(
    user_id: UUID,
    body: UserUpdateRequest,
    _user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN, UserRole.AGENCY_MANAGER)),
    service: UserService = Depends(_get_user_service),
) -> dict:
    user = await service.update_user(user_id, body)
    return {"success": True, "data": _to_user_response(user)}


# ── DELETE /users/:id ────────────────────────────────────

@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    _user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN, UserRole.AGENCY_MANAGER)),
    service: UserService = Depends(_get_user_service),
) -> None:
    await service.delete_user(user_id)


# ── GET /roles (separate router, mounted at /api/v1/roles) ──

@roles_router.get("", response_model=ApiResponse[list[RoleResponse]])
async def list_roles(
    _user: User = Depends(get_current_user),
    service: OrgService = Depends(_get_org_service),
) -> dict:
    roles = await service.list_roles()
    return {
        "success": True,
        "data": [
            RoleResponse(
                id=str(r.id),
                name=r.name,
                permissions=r.permissions,
                description=r.description,
            )
            for r in roles
        ],
    }
