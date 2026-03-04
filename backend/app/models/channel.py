import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid
from app.models.enums import ChannelEventType, ChannelStatus, PlatformType


class Channel(Base, TimestampMixin):
    __tablename__ = "channels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    platform: Mapped[PlatformType] = mapped_column(Enum(PlatformType), nullable=False)
    platform_account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[ChannelStatus] = mapped_column(
        Enum(ChannelStatus), nullable=False, default=ChannelStatus.DISCONNECTED
    )
    access_token_enc: Mapped[str | None] = mapped_column(Text)
    refresh_token_enc: Mapped[str | None] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)

    histories: Mapped[list["ChannelHistory"]] = relationship(back_populates="channel", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("organization_id", "platform", "platform_account_id", name="uq_channel_org_platform_account"),
        Index("idx_channels_org_id", "organization_id"),
        Index("idx_channels_status", "status"),
    )


class ChannelHistory(Base, TimestampMixin):
    __tablename__ = "channel_histories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    event_type: Mapped[ChannelEventType] = mapped_column(Enum(ChannelEventType), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    channel: Mapped["Channel"] = relationship(back_populates="histories")

    __table_args__ = (
        Index("idx_channel_histories_channel_id", "channel_id"),
        Index("idx_channel_histories_org_id", "organization_id"),
    )
