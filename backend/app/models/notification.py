"""Notification and NotificationSetting ORM models (Phase 1-B)."""

import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid
from app.models.enums import NotificationChannel, NotificationType


class Notification(Base):
    """In-app notifications with type/channel classification."""

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    type: Mapped[NotificationType] = mapped_column(nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(
        default=NotificationChannel.IN_APP, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    action_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    __table_args__ = (
        Index("idx_notifications_org_id", "organization_id"),
        Index("idx_notifications_user_id", "user_id"),
        Index("idx_notifications_is_read", "is_read"),
        Index("idx_notifications_type", "type"),
        Index("idx_notifications_created_at", "created_at"),
        Index("idx_notifications_user_unread", "user_id", "is_read", "created_at",
              postgresql_where=text("is_read = false")),
    )


class NotificationSetting(Base, TimestampMixin):
    """Per-user notification preferences (channels, telegram, web push)."""

    __tablename__ = "notification_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    channels: Mapped[dict] = mapped_column(
        JSONB,
        default=lambda: {
            "web": {"enabled": True},
            "email": {"enabled": True},
            "telegram": {"enabled": False},
            "webPush": {"enabled": False},
        },
        nullable=False,
    )
    push_subscription: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_notification_settings_org_user"),
        Index("idx_notification_settings_user_id", "user_id"),
    )
