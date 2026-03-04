"""Organizations API — 4 endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import require_roles
from app.models.enums import UserRole
from app.models.user import Organization, User
from app.repositories.org_repository import OrgRepository
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta
from app.schemas.organization import OrgCreateRequest, OrgResponse, OrgUpdateRequest
from app.services.org_service import OrgService

router = APIRouter()


def _get_org_service(db: AsyncSession = Depends(get_db_session)) -> OrgService:
    return OrgService(OrgRepository(db))


def _to_org_response(o: Organization) -> OrgResponse:
    return OrgResponse(
        id=str(o.id),
        name=o.name,
        slug=o.slug,
        status=o.status.value,
        plan=o.plan.value,
        logo_url=o.logo_url,
        contact_email=o.contact_email,
        contact_phone=o.contact_phone,
        storage_used_bytes=o.storage_used_bytes,
        storage_quota_bytes=o.storage_quota_bytes,
        agency_id=str(o.agency_id) if o.agency_id else None,
        created_at=o.created_at.isoformat(),
    )


# ── GET /organizations ───────────────────────────────────

@router.get("", response_model=PaginatedResponse[OrgResponse])
async def list_organizations(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN, UserRole.AGENCY_MANAGER)),
    service: OrgService = Depends(_get_org_service),
) -> dict:
    orgs, total = await service.list_orgs(page=page, limit=limit)
    return {
        "success": True,
        "data": [_to_org_response(o) for o in orgs],
        "meta": PaginationMeta(
            total=total,
            page=page,
            limit=limit,
            total_pages=(total + limit - 1) // limit,
        ),
    }


# ── POST /organizations ─────────────────────────────────

@router.post("", response_model=ApiResponse[OrgResponse], status_code=201)
async def create_organization(
    body: OrgCreateRequest,
    _user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
    service: OrgService = Depends(_get_org_service),
) -> dict:
    org = await service.create_org(body)
    return {"success": True, "data": _to_org_response(org)}


# ── PUT /organizations/:id ──────────────────────────────

@router.put("/{org_id}", response_model=ApiResponse[OrgResponse])
async def update_organization(
    org_id: UUID,
    body: OrgUpdateRequest,
    _user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN, UserRole.AGENCY_MANAGER)),
    service: OrgService = Depends(_get_org_service),
) -> dict:
    org = await service.update_org(org_id, body)
    return {"success": True, "data": _to_org_response(org)}


# ── DELETE /organizations/:id ────────────────────────────

@router.delete("/{org_id}", status_code=204)
async def delete_organization(
    org_id: UUID,
    _user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
    service: OrgService = Depends(_get_org_service),
) -> None:
    await service.delete_org(org_id)
