"""Notifications API — 5 endpoints (S10, F13)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import WorkspaceContext, get_workspace_context
from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta
from app.schemas.notification import NotificationResponse, UnreadCountResponse
from app.services.notification_service import NotificationService

router = APIRouter()


def _get_service(db: AsyncSession = Depends(get_db_session)) -> NotificationService:
    return NotificationService(NotificationRepository(db))


def _to_notification_response(n: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=str(n.id),
        organization_id=str(n.organization_id),
        user_id=str(n.user_id),
        type=n.type.value,
        channel=n.channel.value,
        title=n.title,
        message=n.message,
        payload=n.payload,
        is_read=n.is_read,
        read_at=n.read_at if isinstance(n.read_at, str) else (n.read_at.isoformat() if n.read_at else None),
        action_url=n.action_url,
        created_at=n.created_at if isinstance(n.created_at, str) else n.created_at.isoformat(),
    )


# ── GET /notifications ─────────────────────────────────
@router.get("", response_model=PaginatedResponse[NotificationResponse])
async def list_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    type: str | None = Query(None, alias="type"),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: NotificationService = Depends(_get_service),
) -> dict:
    """Get paginated list of notifications for the current user."""
    notifications, total = await service.list_notifications(
        workspace.org_id, workspace.user.id, page=page, limit=limit, type_filter=type
    )
    return {
        "success": True,
        "data": [_to_notification_response(n) for n in notifications],
        "meta": PaginationMeta(
            total=total, page=page, limit=limit, total_pages=(total + limit - 1) // limit
        ),
    }


# ── PATCH /notifications/:id/read ──────────────────────
@router.patch("/{notification_id}/read", response_model=ApiResponse[NotificationResponse])
async def mark_notification_read(
    notification_id: UUID,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: NotificationService = Depends(_get_service),
) -> dict:
    """Mark a single notification as read."""
    notification = await service.mark_read(notification_id, workspace.org_id, workspace.user.id)
    return {"success": True, "data": _to_notification_response(notification)}


# ── POST /notifications/mark-all-read ──────────────────
@router.post("/mark-all-read", response_model=ApiResponse[dict])
async def mark_all_notifications_read(
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: NotificationService = Depends(_get_service),
) -> dict:
    """Mark all unread notifications as read for the current user."""
    count = await service.mark_all_read(workspace.org_id, workspace.user.id)
    return {"success": True, "data": {"affected": count}}


# ── GET /notifications/unread-count ────────────────────
@router.get("/unread-count", response_model=ApiResponse[UnreadCountResponse])
async def get_unread_count(
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: NotificationService = Depends(_get_service),
) -> dict:
    """Get the count of unread notifications for the current user."""
    count = await service.count_unread(workspace.org_id, workspace.user.id)
    return {"success": True, "data": UnreadCountResponse(count=count)}
