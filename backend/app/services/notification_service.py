"""Notification business logic — S10 (F13/F07).

4-channel notification routing:
  1. IN_APP — DB record + SSE (always)
  2. Web Push — pywebpush (if webPush enabled + push_subscription present)
  3. Telegram — python-telegram-bot (if telegram enabled + chat_id present)
  4. Email — FastAPI-Mail (if email enabled + user email available)
"""

from uuid import UUID

import structlog

from app.api.v1.sse import publish_sse_event
from app.core.exceptions import NotFoundError
from app.integrations import telegram
from app.integrations.email.service import send_notification_email
from app.integrations.webpush import send_web_push
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
        """Create a notification and dispatch it via all enabled channels.

        Routing order:
          1. IN_APP — DB record + SSE (always)
          2. Web Push — pywebpush (if enabled + subscription present)
          3. Telegram — Bot API (if enabled + chat_id present)
          4. Email — FastAPI-Mail (if enabled + user email available)
        """
        # 1. Create in-app notification
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

        # 2. Publish SSE event for real-time in-app notification
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

        # Load user notification settings for channel routing
        user_settings = await self._repo.get_settings(org_id, user_id)
        if user_settings:
            channels_config = user_settings.channels or {}

            # 3. Web Push
            web_push_config = channels_config.get("webPush", {})
            if web_push_config.get("enabled", False) and user_settings.push_subscription:
                try:
                    await send_web_push(
                        subscription_info=user_settings.push_subscription,
                        title=title,
                        message=message,
                        url=action_url,
                    )
                except Exception:
                    logger.warning("notification_webpush_failed", user_id=str(user_id), exc_info=True)

            # 4. Telegram
            telegram_config = channels_config.get("telegram", {})
            if telegram_config.get("enabled", False) and user_settings.telegram_chat_id:
                try:
                    telegram_text = f"<b>{title}</b>\n{message}"
                    if action_url:
                        telegram_text += f"\n\n<a href='{action_url}'>자세히 보기</a>"
                    await telegram.send_message(user_settings.telegram_chat_id, telegram_text)
                except Exception:
                    logger.warning("notification_telegram_failed", user_id=str(user_id), exc_info=True)

            # 5. Email
            email_config = channels_config.get("email", {})
            if email_config.get("enabled", False):
                try:
                    user_email = await self._repo.get_user_email(user_id)
                    if user_email:
                        await send_notification_email(
                            email=user_email,
                            title=title,
                            message=message,
                            action_url=action_url,
                        )
                except Exception:
                    logger.warning("notification_email_failed", user_id=str(user_id), exc_info=True)

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
        """Update notification settings (upsert).

        Supports: channels, telegram_chat_id, push_subscription.
        """
        update_data: dict = {}
        if "channels" in data and data["channels"] is not None:
            update_data["channels"] = data["channels"]
        if "telegram_chat_id" in data and data["telegram_chat_id"] is not None:
            update_data["telegram_chat_id"] = data["telegram_chat_id"]
        if "push_subscription" in data:
            # Allow null to clear subscription
            update_data["push_subscription"] = data["push_subscription"]

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
