from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import engine, get_db_session
from app.core.deps import WorkspaceContext, get_workspace_context, require_roles
from app.core.rate_limit import limiter
from app.core.redis import redis_client
from app.models.enums import UserRole
from app.models.user import SystemAnnouncement, User
from app.repositories.ai_usage_repository import AiUsageRepository
from app.repositories.org_repository import OrgRepository
from app.schemas.ai import AiUsageResponse
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta
from app.schemas.dashboard import AnnouncementCreateRequest, AnnouncementResponse
from app.schemas.organization import AgencyCreateRequest, AgencyResponse
from app.services.ai_service import AiService
from app.services.org_service import OrgService

router = APIRouter()


def _get_org_service(db: AsyncSession = Depends(get_db_session)) -> OrgService:
    return OrgService(OrgRepository(db))


@router.get("/health", response_model=ApiResponse[dict])
async def health_check() -> dict:
    """Check DB and Redis connectivity."""
    checks: dict[str, str] = {}

    # PostgreSQL
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # Redis
    try:
        pong = await redis_client.ping()
        checks["redis"] = "ok" if pong else "error"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())

    return {
        "success": all_ok,
        "data": {
            "status": "healthy" if all_ok else "degraded",
            "services": checks,
        },
    }


# ── GET /admin/agencies ──────────────────────────────────

@router.get("/agencies", response_model=PaginatedResponse[AgencyResponse])
async def list_agencies(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
    service: OrgService = Depends(_get_org_service),
) -> dict:
    agencies, total = await service.list_agencies(page=page, limit=limit)
    return {
        "success": True,
        "data": [
            AgencyResponse(
                id=str(a.id),
                name=a.name,
                contact_email=a.contact_email,
                contact_phone=a.contact_phone,
                is_active=a.is_active,
                created_at=a.created_at.isoformat(),
            )
            for a in agencies
        ],
        "meta": PaginationMeta(
            total=total,
            page=page,
            limit=limit,
            total_pages=(total + limit - 1) // limit,
        ),
    }


# ── POST /admin/agencies ─────────────────────────────────

@router.post("/agencies", response_model=ApiResponse[AgencyResponse], status_code=201)
async def create_agency(
    body: AgencyCreateRequest,
    _user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
    service: OrgService = Depends(_get_org_service),
) -> dict:
    agency = await service.create_agency(body)
    return {
        "success": True,
        "data": AgencyResponse(
            id=str(agency.id),
            name=agency.name,
            contact_email=agency.contact_email,
            contact_phone=agency.contact_phone,
            is_active=agency.is_active,
            created_at=agency.created_at.isoformat(),
        ),
    }


def _to_announcement_response(a: SystemAnnouncement) -> AnnouncementResponse:
    return AnnouncementResponse(
        id=str(a.id),
        title=a.title,
        content=a.content,
        type=a.type,
        is_active=a.is_active,
        publish_at=a.publish_at.isoformat() if a.publish_at else None,
        created_by=str(a.created_by) if a.created_by else None,
        created_at=a.created_at.isoformat(),
    )


# ── GET /admin/announcements ────────────────────────────

@router.get("/announcements", response_model=ApiResponse[list[AnnouncementResponse]])
async def list_announcements(
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    stmt = select(SystemAnnouncement).where(
        SystemAnnouncement.is_active.is_(True)
    ).order_by(SystemAnnouncement.created_at.desc())
    result = await db.execute(stmt)
    announcements = result.scalars().all()
    return {"success": True, "data": [_to_announcement_response(a) for a in announcements]}


# ── POST /admin/announcements ───────────────────────────

@router.post("/announcements", response_model=ApiResponse[AnnouncementResponse], status_code=201)
async def create_announcement(
    body: AnnouncementCreateRequest,
    _user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    from datetime import datetime

    announcement = SystemAnnouncement(
        title=body.title,
        content=body.content,
        type=body.type,
        is_active=body.is_active,
        publish_at=datetime.fromisoformat(body.publish_at) if body.publish_at else None,
        created_by=workspace.user.id,
    )
    db.add(announcement)
    await db.flush()
    return {"success": True, "data": _to_announcement_response(announcement)}


# ── GET /admin/ai-usage ───────────────────────────────────

def _get_ai_service(db: AsyncSession = Depends(get_db_session)) -> AiService:
    return AiService(AiUsageRepository(db))


@router.get("/ai-usage", response_model=ApiResponse[AiUsageResponse])
async def get_ai_usage(
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
    service: AiService = Depends(_get_ai_service),
) -> dict:
    """Get aggregated AI usage statistics for an organization (SA only)."""
    result = await service.get_usage_stats(workspace.org_id)
    return {"success": True, "data": result}


# ── GET /admin/rate-limits ──────────────────────────────

@router.get("/rate-limits", response_model=ApiResponse[dict])
async def get_rate_limits(
    _user: User = Depends(require_roles(UserRole.SYSTEM_ADMIN)),
) -> dict:
    """Get current Rate Limit status from Redis (SA only).

    Returns global rate limit counters and slowapi configuration.
    """
    rate_limit_info: dict = {
        "default_limits": [],
        "active_keys": 0,
    }

    # Collect slowapi default limits
    if hasattr(limiter, "_default_limits") and limiter._default_limits:
        rate_limit_info["default_limits"] = [
            str(lim) for lim in limiter._default_limits
        ]

    # Count rate-limit keys in Redis
    try:
        cursor = 0
        count = 0
        while True:
            cursor, keys = await redis_client.scan(cursor, match="LIMITER*", count=100)
            count += len(keys)
            if cursor == 0:
                break
        rate_limit_info["active_keys"] = count
    except Exception:
        rate_limit_info["active_keys"] = -1  # Indicates Redis scan error

    return {"success": True, "data": rate_limit_info}
