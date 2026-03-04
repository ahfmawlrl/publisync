"""Analytics API — 7 endpoints (S12 F06 + Phase 3 F18/F20 + Phase 4 F23)."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import WorkspaceContext, get_workspace_context, require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import EngagementHeatmapItem, PerformanceDataResponse
from app.schemas.common import ApiResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter()


def _get_service(db: AsyncSession = Depends(get_db_session)) -> AnalyticsService:
    return AnalyticsService(AnalyticsRepository(db))


# ── GET /analytics/performance ─────────────────────────
@router.get("/performance", response_model=ApiResponse[list[PerformanceDataResponse]])
async def get_performance(
    platform: str | None = Query(None),
    period: str = Query("30d"),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: AnalyticsService = Depends(_get_service),
) -> dict:
    data = await service.get_performance(workspace.org_id, platform=platform, period=period)
    return {"success": True, "data": data}


# ── GET /analytics/engagement-heatmap ──────────────────
@router.get("/engagement-heatmap", response_model=ApiResponse[list[EngagementHeatmapItem]])
async def get_engagement_heatmap(
    period: str = Query("30d"),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: AnalyticsService = Depends(_get_service),
) -> dict:
    data = await service.get_engagement_heatmap(workspace.org_id, period=period)
    return {"success": True, "data": data}


# ── GET /analytics/performance/export ──────────────────
@router.get("/performance/export")
async def export_performance(
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    period: str = Query("30d"),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user=Depends(require_roles(UserRole.SYSTEM_ADMIN, UserRole.AGENCY_MANAGER)),
    service: AnalyticsService = Depends(_get_service),
) -> StreamingResponse:
    csv_data = await service.export_performance(workspace.org_id, format=format, period=period)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=performance_{period}.csv"},
    )


# ── Phase 3 — Sentiment Trend (F18) ──────────────────
@router.get("/sentiment-trend")
async def get_sentiment_trend(
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: AnalyticsService = Depends(_get_service),
) -> dict:
    data = await service.get_sentiment_trend(workspace.org_id, period=period)
    return {"success": True, "data": data}


# ── Phase 3 — Prediction (F20) ───────────────────────
@router.get("/prediction")
async def get_prediction(
    content_id: str | None = Query(None),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: AnalyticsService = Depends(_get_service),
) -> dict:
    data = await service.get_prediction(workspace.org_id, content_id=content_id)
    return {"success": True, "data": data}


# ── Phase 4 — Benchmark (F23) ───────────────────────


@router.get("/benchmark")
async def get_benchmark(
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(
        require_roles(UserRole.AGENCY_MANAGER, UserRole.CLIENT_DIRECTOR)
    ),
    service: AnalyticsService = Depends(_get_service),
) -> dict:
    """Benchmark analysis — compare org performance vs industry average."""
    data = await service.get_benchmark(workspace.org_id, period=period)
    return {"success": True, "data": data}


@router.get("/benchmark/organizations")
async def get_benchmark_organizations(
    period: str = Query("30d", pattern="^(7d|30d|90d)$"),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER)),
    service: AnalyticsService = Depends(_get_service),
) -> dict:
    """Organization comparison — AM only, compare managed orgs."""
    # Get organizations managed by the current user
    from sqlalchemy import select
    from app.models.user import UserOrganization

    stmt = select(UserOrganization.organization_id).where(
        UserOrganization.user_id == workspace.user.id,
    )
    result = await service._repo._db.execute(stmt)
    org_ids = [row[0] for row in result.all()]

    if not org_ids:
        org_ids = [workspace.org_id]

    data = await service.get_org_comparison(org_ids, period=period)
    return {"success": True, "data": data}
