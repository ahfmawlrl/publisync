"""Calendar Event ORM model (Phase 2, F10).

Table: calendar_events — stores scheduled posts, holidays, and custom events.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, generate_uuid
from app.models.enums import CalendarEventType


class CalendarEvent(Base, TimestampMixin):
    """Calendar event for content scheduling, holidays, and custom markers."""

    __tablename__ = "calendar_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    content_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contents.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[CalendarEventType] = mapped_column(
        Enum(CalendarEventType), nullable=False, default=CalendarEventType.CUSTOM
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE")
    is_holiday: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)  # hex color for UI
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    __table_args__ = (
        Index("idx_calendar_events_org_id", "organization_id"),
        Index("idx_calendar_events_content_id", "content_id"),
        Index("idx_calendar_events_event_date", "event_date"),
        Index("idx_calendar_events_event_type", "event_type"),
        Index("idx_calendar_events_org_date", "organization_id", "event_date"),
    )
