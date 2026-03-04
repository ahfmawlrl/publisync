"""Notification Settings API — 4 endpoints (S10, F13/F07)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import WorkspaceContext, get_workspace_context, require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.notification_repository import NotificationRepository
from app.schemas.common import ApiResponse
from app.schemas.notification import (
    NotificationSettingResponse,
    NotificationSettingUpdateRequest,
    TelegramChannelConfigRequest,
    TelegramTestRequest,
)
from app.services.notification_service import NotificationService

router = APIRouter()


def _get_service(db: AsyncSession = Depends(get_db_session)) -> NotificationService:
    return NotificationService(NotificationRepository(db))


# ── GET /notification-settings ─────────────────────────
@router.get("", response_model=ApiResponse[NotificationSettingResponse])
async def get_notification_settings(
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: NotificationService = Depends(_get_service),
) -> dict:
    """Get notification settings for the current user."""
    settings = await service.get_settings(workspace.org_id, workspace.user.id)
    return {"success": True, "data": settings}


# ── PUT /notification-settings ─────────────────────────
@router.put("", response_model=ApiResponse[NotificationSettingResponse])
async def update_notification_settings(
    body: NotificationSettingUpdateRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: NotificationService = Depends(_get_service),
) -> dict:
    """Update notification settings for the current user."""
    settings = await service.update_settings(
        workspace.org_id, workspace.user.id, body.model_dump(exclude_unset=True)
    )
    return {"success": True, "data": settings}


# ── POST /notification-settings/telegram/test ──────────
@router.post("/telegram/test", response_model=ApiResponse[dict])
async def send_telegram_test(
    body: TelegramTestRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: NotificationService = Depends(_get_service),
) -> dict:
    """Send a test message to verify Telegram bot configuration."""
    success = await service.send_telegram_test(body.chat_id)
    return {
        "success": True,
        "data": {
            "sent": success,
            "message": "테스트 메시지가 전송되었습니다." if success else "테스트 메시지 전송에 실패했습니다.",
        },
    }


# ── POST /notification-settings/telegram/channels ─────
@router.post("/telegram/channels", response_model=ApiResponse[dict])
async def configure_telegram_channels(
    body: TelegramChannelConfigRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _am: User = Depends(require_roles(UserRole.SYSTEM_ADMIN, UserRole.AGENCY_MANAGER)),
    service: NotificationService = Depends(_get_service),
) -> dict:
    """Configure Telegram notification channel for the organization (AM+ only).

    Updates the current user's Telegram settings with the provided chat_id and enabled state.
    """
    update_data = {
        "telegram_chat_id": body.chat_id,
        "channels": {
            "web": {"enabled": True},
            "email": {"enabled": True},
            "telegram": {"enabled": body.enabled},
            "webPush": {"enabled": False},
        },
    }
    settings = await service.update_settings(workspace.org_id, workspace.user.id, update_data)
    return {"success": True, "data": settings}
