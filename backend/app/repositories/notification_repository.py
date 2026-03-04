"""Repository for Notification, NotificationSetting — S10 (F13/F07)."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationSetting


class NotificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Notification ──────────────────────────────────────

    async def list_notifications(
        self,
        org_id: UUID,
        user_id: UUID,
        offset: int = 0,
        limit: int = 20,
        type_filter: str | None = None,
    ) -> tuple[list[Notification], int]:
        base = select(Notification).where(
            Notification.organization_id == org_id,
            Notification.user_id == user_id,
        )
        count_base = select(func.count()).select_from(Notification).where(
            Notification.organization_id == org_id,
            Notification.user_id == user_id,
        )

        if type_filter:
            base = base.where(Notification.type == type_filter)
            count_base = count_base.where(Notification.type == type_filter)

        total = (await self._db.execute(count_base)).scalar() or 0
        stmt = base.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_notification(self, notification_id: UUID) -> Notification | None:
        return await self._db.get(Notification, notification_id)

    async def mark_read(self, notification_id: UUID) -> Notification | None:
        notification = await self.get_notification(notification_id)
        if notification is None:
            return None
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc).isoformat()
        await self._db.flush()
        return notification

    async def mark_all_read(self, org_id: UUID, user_id: UUID) -> int:
        stmt = (
            update(Notification)
            .where(
                and_(
                    Notification.organization_id == org_id,
                    Notification.user_id == user_id,
                    Notification.is_read.is_(False),
                )
            )
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        result = await self._db.execute(stmt)
        await self._db.flush()
        return result.rowcount  # type: ignore[return-value]

    async def count_unread(self, org_id: UUID, user_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.organization_id == org_id,
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        result = await self._db.execute(stmt)
        return result.scalar() or 0

    async def create_notification(self, notification: Notification) -> Notification:
        self._db.add(notification)
        await self._db.flush()
        return notification

    # ── NotificationSetting ───────────────────────────────

    async def get_settings(self, org_id: UUID, user_id: UUID) -> NotificationSetting | None:
        stmt = select(NotificationSetting).where(
            NotificationSetting.organization_id == org_id,
            NotificationSetting.user_id == user_id,
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_settings(
        self,
        org_id: UUID,
        user_id: UUID,
        data: dict,
    ) -> NotificationSetting:
        """Insert or update notification settings using PostgreSQL ON CONFLICT."""
        insert_values: dict = {
            "organization_id": org_id,
            "user_id": user_id,
            **data,
        }

        stmt = (
            pg_insert(NotificationSetting)
            .values(**insert_values)
            .on_conflict_do_update(
                constraint="uq_notification_settings_org_user",
                set_={k: v for k, v in data.items()},
            )
            .returning(NotificationSetting)
        )
        result = await self._db.execute(stmt)
        await self._db.flush()

        # Re-fetch the full object to ensure it's attached to the session
        setting = result.scalar_one()
        return setting
