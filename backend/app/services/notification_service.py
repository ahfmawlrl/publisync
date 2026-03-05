"""Notification business logic — S10 (F13/F07)."""

from uuid import UUID

import structlog

from app.api.v1.sse import publish_sse_event
from app.core.exceptions import NotFoundError
from app.integrations import telegram
from app.models.enums import NotificationChannel, NotificationType
from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository

logger = structlog.get_logger()


class NotificationNotFoundError(NotFoundError):
    detail = "Notification not found"


class NotificationService:
    def __init__(self, repo: NotificationRepository) -> None:
        self._repo = repo

    async def list_notifications(
        self,
        org_id: UUID,
        user_id: UUID,
        page: int = 1,
        limit: int = 20,
        type_filter: str | None = None,
    ) -> tuple[list[Notification], int]:
        offset = (page - 1) * limit
        return await self._repo.list_notifications(
            org_id, user_id, offset=offset, limit=limit, type_filter=type_filter
        )

    async def mark_read(self, notification_id: UUID, org_id: UUID, user_id: UUID) -> Notification:
        notification = await self._repo.get_notification(notification_id)
        if notification is None:
            raise NotificationNotFoundError()
        if notification.organization_id != org_id or notification.user_id != user_id:
            raise NotificationNotFoundError()

        notification = await self._repo.mark_read(notification_id)
        if notification is None:
            raise NotificationNotFoundError()

        logger.info("notification_marked_read", notification_id=str(notification_id))
        return notification

    async def mark_all_read(self, org_id: UUID, user_id: UUID) -> int:
        count = await self._repo.mark_all_read(org_id, user_id)
        logger.info("notifications_marked_all_read", user_id=str(user_id), count=count)
        return count

    async def count_unread(self, org_id: UUID, user_id: UUID) -> int:
        return await self._repo.count_unread(org_id, user_id)

    async def create_and_dispatch(
        self,
        org_id: UUID,
        user_id: UUID,
        type_: NotificationType,
        title: str,
        message: str,
        payload: dict | None = None,
        action_url: str | None = None,
    ) -> Notification:
        """Create a notification and dispatch it via SSE (and optionally Telegram).

        This is the primary method for other services to create notifications.
        It creates an in-app notification record and publishes an SSE event.
        If the user has Telegram enabled, it also sends a Telegram message.
        """
        notification = Notification(
            organization_id=org_id,
            user_id=user_id,
            type=type_,
            channel=NotificationChannel.IN_APP,
            title=title,
            message=message,
            payload=payload,
            action_url=action_url,
        )
        notification = await self._repo.create_notification(notification)

        # Publish SSE event for real-time in-app notification
        await publish_sse_event(
            org_id=str(org_id),
            user_id=str(user_id),
            event_type="notification",
            data={
                "notification_id": str(notification.id),
                "type": type_.value,
                "title": title,
                "message": message,
                "action_url": action_url,
            },
        )

        # Check if user has Telegram enabled and send there too
        settings = await self._repo.get_settings(org_id, user_id)
        if settings and settings.telegram_chat_id:
            telegram_config = settings.channels.get("telegram", {})
            if telegram_config.get("enabled", False):
                telegram_text = f"<b>{title}</b>\n{message}"
                if action_url:
                    telegram_text += f"\n\n<a href='{action_url}'>자세히 보기</a>"
                await telegram.send_message(settings.telegram_chat_id, telegram_text)

        logger.info(
            "notification_created",
            notification_id=str(notification.id),
            type=type_.value,
            user_id=str(user_id),
        )
        return notification

    async def get_settings(self, org_id: UUID, user_id: UUID) -> dict:
        """Get notification settings, returning defaults if none exist."""
        settings = await self._repo.get_settings(org_id, user_id)
        if settings is None:
            return {
                "id": None,
                "organization_id": str(org_id),
                "user_id": str(user_id),
                "channels": {
                    "web": {"enabled": True},
                    "email": {"enabled": True},
                    "telegram": {"enabled": False},
                    "webPush": {"enabled": False},
                },
                "push_subscription": None,
                "telegram_chat_id": None,
            }
        return {
            "id": str(settings.id),
            "organization_id": str(settings.organization_id),
            "user_id": str(settings.user_id),
            "channels": settings.channels,
            "push_subscription": settings.push_subscription,
            "telegram_chat_id": settings.telegram_chat_id,
        }

    async def update_settings(
        self,
        org_id: UUID,
        user_id: UUID,
        data: dict,
    ) -> dict:
        """Update notification settings (upsert)."""
        update_data: dict = {}
        if "channels" in data and data["channels"] is not None:
            update_data["channels"] = data["channels"]
        if "telegram_chat_id" in data and data["telegram_chat_id"] is not None:
            update_data["telegram_chat_id"] = data["telegram_chat_id"]

        if not update_data:
            return await self.get_settings(org_id, user_id)

        await self._repo.upsert_settings(org_id, user_id, update_data)
        logger.info("notification_settings_updated", user_id=str(user_id))
        return await self.get_settings(org_id, user_id)

    async def send_telegram_test(self, chat_id: str) -> bool:
        """Send a test message to verify Telegram configuration."""
        text = (
            "<b>PubliSync 텔레그램 알림 테스트</b>\n\n"
            "이 메시지가 보이면 텔레그램 알림이 정상적으로 설정되었습니다."
        )
        success = await telegram.send_message(chat_id, text)
        if success:
            logger.info("telegram_test_sent", chat_id=chat_id)
        else:
            logger.warning("telegram_test_failed", chat_id=chat_id)
        return success
