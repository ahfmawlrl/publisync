"""Dashboard API — 8 endpoints (S3 badge-counts + S7 expansion)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import WorkspaceContext, get_workspace_context, require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.org_repository import OrgRepository
from app.schemas.common import ApiResponse
from app.schemas.dashboard import (
    ApprovalStatusItem,
    DashboardSummaryResponse,
    OrgSummaryItem,
    PlatformTrendItem,
    RecentContentItem,
    SentimentSummaryItem,
    TodayScheduleItem,
)
from app.schemas.organization import BadgeCountsResponse
from app.services.dashboard_service import DashboardService
from app.services.org_service import OrgService

router = APIRouter()


def _get_dashboard_service(db: AsyncSession = Depends(get_db_session)) -> DashboardService:
    return DashboardService(db)


def _get_org_service(db: AsyncSession = Depends(get_db_session)) -> OrgService:
    return OrgService(OrgRepository(db))


# ── GET /dashboard/badge-counts ──────────────────────────
@router.get("/badge-counts", response_model=ApiResponse[BadgeCountsResponse])
async def get_badge_counts(
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: OrgService = Depends(_get_org_service),
) -> dict:
    counts = await service.get_badge_counts(workspace.org_id, workspace.user_role)
    return {"success": True, "data": counts}


# ── GET /dashboard/summary ───────────────────────────────
@router.get("/summary", response_model=ApiResponse[DashboardSummaryResponse])
async def get_summary(
    period: str = Query("7d", pattern=r"^(7d|30d)$"),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: DashboardService = Depends(_get_dashboard_service),
) -> dict:
    summary = await service.get_summary(workspace.org_id, period=period)
    return {"success": True, "data": summary}


# ── GET /dashboard/platform-trends ───────────────────────
@router.get("/platform-trends", response_model=ApiResponse[list[PlatformTrendItem]])
async def get_platform_trends(
    period: str = Query("7d", pattern=r"^(7d|30d)$"),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: DashboardService = Depends(_get_dashboard_service),
) -> dict:
    trends = await service.get_platform_trends(workspace.org_id, period=period)
    return {"success": True, "data": trends}


# ── GET /dashboard/approval-status ───────────────────────
@router.get("/approval-status", response_model=ApiResponse[list[ApprovalStatusItem]])
async def get_approval_status(
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: DashboardService = Depends(_get_dashboard_service),
) -> dict:
    statuses = await service.get_approval_status(workspace.org_id)
    return {"success": True, "data": statuses}


# ── GET /dashboard/recent-contents ───────────────────────
@router.get("/recent-contents", response_model=ApiResponse[list[RecentContentItem]])
async def get_recent_contents(
    limit: int = Query(10, ge=1, le=50),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: DashboardService = Depends(_get_dashboard_service),
) -> dict:
    contents = await service.get_recent_contents(workspace.org_id, limit=limit)
    return {"success": True, "data": contents}


# ── GET /dashboard/today-schedule ────────────────────────
@router.get("/today-schedule", response_model=ApiResponse[list[TodayScheduleItem]])
async def get_today_schedule(
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: DashboardService = Depends(_get_dashboard_service),
) -> dict:
    schedule = await service.get_today_schedule(workspace.org_id)
    return {"success": True, "data": schedule}


# ── GET /dashboard/sentiment-summary ─────────────────────
@router.get("/sentiment-summary", response_model=ApiResponse[list[SentimentSummaryItem]])
async def get_sentiment_summary(
    period: str = Query("7d", pattern=r"^(7d|30d)$"),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: DashboardService = Depends(_get_dashboard_service),
) -> dict:
    """Comment sentiment distribution for donut chart (Phase 1-B)."""
    data = await service.get_sentiment_summary(workspace.org_id, period=period)
    return {"success": True, "data": data}


# ── GET /dashboard/all-organizations ─────────────────────
@router.get("/all-organizations", response_model=ApiResponse[list[OrgSummaryItem]])
async def get_all_organizations(
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.SYSTEM_ADMIN)),
    service: DashboardService = Depends(_get_dashboard_service),
) -> dict:
    summaries = await service.get_all_organizations_summary()
    return {"success": True, "data": summaries}
