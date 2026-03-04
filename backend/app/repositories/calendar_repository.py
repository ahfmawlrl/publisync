"""Repository for CalendarEvent — S16 (F10, Phase 2)."""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar import CalendarEvent
from app.models.enums import CalendarEventType


class CalendarRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_events(
        self,
        org_id: UUID,
        start_date: date,
        end_date: date,
        event_type: str | None = None,
    ) -> list[CalendarEvent]:
        """List calendar events for an organization within a date range."""
        stmt = select(CalendarEvent).where(
            CalendarEvent.organization_id == org_id,
            CalendarEvent.event_date >= start_date,
            CalendarEvent.event_date <= end_date,
        )

        if event_type:
            stmt = stmt.where(CalendarEvent.event_type == event_type)

        stmt = stmt.order_by(CalendarEvent.event_date.asc(), CalendarEvent.scheduled_at.asc())
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_event(self, event_id: UUID, org_id: UUID) -> CalendarEvent | None:
        """Get a single calendar event by ID and organization."""
        stmt = select(CalendarEvent).where(
            CalendarEvent.id == event_id,
            CalendarEvent.organization_id == org_id,
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_event(self, data: dict) -> CalendarEvent:
        """Create a new calendar event."""
        event = CalendarEvent(**data)
        self._db.add(event)
        await self._db.flush()
        return event

    async def update_event(self, event_id: UUID, org_id: UUID, data: dict) -> CalendarEvent | None:
        """Update an existing calendar event. Returns None if not found."""
        event = await self.get_event(event_id, org_id)
        if event is None:
            return None

        for key, value in data.items():
            setattr(event, key, value)
        await self._db.flush()
        return event

    async def delete_events_by_type(self, org_id: UUID, event_type: str) -> int:
        """Delete all events of a given type for an organization. Used for holiday bulk replace."""
        stmt = (
            delete(CalendarEvent)
            .where(
                CalendarEvent.organization_id == org_id,
                CalendarEvent.event_type == event_type,
                CalendarEvent.is_holiday.is_(True),
            )
            .returning(CalendarEvent.id)
        )
        result = await self._db.execute(stmt)
        deleted_rows = result.all()
        await self._db.flush()
        return len(deleted_rows)

    async def count_events_at_time(self, org_id: UUID, scheduled_at: datetime) -> int:
        """Count events scheduled at the exact same time for conflict detection."""
        stmt = (
            select(func.count())
            .select_from(CalendarEvent)
            .where(
                CalendarEvent.organization_id == org_id,
                CalendarEvent.scheduled_at == scheduled_at,
            )
        )
        result = await self._db.execute(stmt)
        return result.scalar() or 0

    async def find_by_content_id(self, content_id: UUID, org_id: UUID) -> CalendarEvent | None:
        """콘텐츠 ID로 연결된 캘린더 이벤트 조회."""
        result = await self._db.execute(
            select(CalendarEvent).where(
                CalendarEvent.content_id == content_id,
                CalendarEvent.organization_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete_by_content_id(self, content_id: UUID, org_id: UUID) -> int:
        """콘텐츠 연결 이벤트 삭제."""
        result = await self._db.execute(
            delete(CalendarEvent).where(
                CalendarEvent.content_id == content_id,
                CalendarEvent.organization_id == org_id,
            )
        )
        return result.rowcount
