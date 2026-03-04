"""Calendar business logic — S16 (F10, Phase 2)."""

import structlog
from datetime import date, datetime
from uuid import UUID

from app.core.exceptions import NotFoundError
from app.models.calendar import CalendarEvent
from app.models.enums import CalendarEventType
from app.repositories.calendar_repository import CalendarRepository

logger = structlog.get_logger()


class CalendarService:
    def __init__(self, repo: CalendarRepository) -> None:
        self._repo = repo

    async def list_events(
        self,
        org_id: UUID,
        start_date: date,
        end_date: date,
        event_type: str | None = None,
    ) -> list[CalendarEvent]:
        """List calendar events within a date range."""
        return await self._repo.list_events(org_id, start_date, end_date, event_type)

    async def reschedule_event(
        self,
        event_id: UUID,
        org_id: UUID,
        new_date: date,
        new_scheduled_at: datetime | None = None,
    ) -> tuple[CalendarEvent, dict | None]:
        """Reschedule an event. Returns (event, conflict_warning) tuple."""
        event = await self._repo.get_event(event_id, org_id)
        if event is None:
            raise NotFoundError("Calendar event not found")

        update_data: dict = {"event_date": new_date}
        if new_scheduled_at is not None:
            update_data["scheduled_at"] = new_scheduled_at

        updated = await self._repo.update_event(event_id, org_id, update_data)
        if updated is None:
            raise NotFoundError("Calendar event not found")

        # Check for scheduling conflicts
        conflict_info = None
        if new_scheduled_at:
            conflict_info = await self.detect_conflicts(org_id, new_scheduled_at)

        logger.info(
            "calendar_event_rescheduled",
            event_id=str(event_id),
            new_date=str(new_date),
        )
        return updated, conflict_info

    async def get_holidays(self, org_id: UUID, year: int) -> list[CalendarEvent]:
        """Get holiday events for a given year."""
        start = date(year, 1, 1)
        end = date(year, 12, 31)
        events = await self._repo.list_events(org_id, start, end)
        return [e for e in events if e.is_holiday]

    async def update_holidays(
        self,
        org_id: UUID,
        holidays: list[dict],
        user_id: UUID,
    ) -> list[CalendarEvent]:
        """Bulk replace custom holidays: delete old ones, create new ones."""
        # Delete existing custom holidays
        deleted_count = await self._repo.delete_events_by_type(
            org_id, CalendarEventType.HOLIDAY.value
        )
        logger.info("calendar_holidays_deleted", org_id=str(org_id), count=deleted_count)

        # Create new holidays
        created: list[CalendarEvent] = []
        for h in holidays:
            event_data = {
                "organization_id": org_id,
                "event_type": CalendarEventType.HOLIDAY,
                "title": h["title"],
                "description": h.get("description"),
                "event_date": h["event_date"],
                "scheduled_at": h.get("scheduled_at"),
                "platform": h.get("platform"),
                "is_holiday": True,
                "is_recurring": h.get("is_recurring", False),
                "color": h.get("color"),
                "created_by": user_id,
                "status": "ACTIVE",
            }
            event = await self._repo.create_event(event_data)
            created.append(event)

        logger.info(
            "calendar_holidays_updated",
            org_id=str(org_id),
            created_count=len(created),
        )
        return created

    async def detect_conflicts(self, org_id: UUID, scheduled_at: datetime) -> dict | None:
        """Detect scheduling conflicts. Warn if 3+ events at the same time."""
        count = await self._repo.count_events_at_time(org_id, scheduled_at)
        if count >= 3:
            return {
                "count": count,
                "warning": f"해당 시간에 이미 {count}개의 이벤트가 예약되어 있습니다.",
            }
        return None

    # ── Content ↔ Calendar sync helpers ──────────────────

    async def create_content_event(
        self,
        org_id: UUID,
        content_id: UUID,
        title: str,
        scheduled_at: datetime,
        platforms: list[str] | None,
        user_id: UUID,
    ) -> CalendarEvent:
        """콘텐츠 예약 게시 시 캘린더 이벤트 자동 생성."""
        event_data = {
            "organization_id": org_id,
            "content_id": content_id,
            "event_type": CalendarEventType.SCHEDULED_POST,
            "title": title,
            "event_date": scheduled_at.date(),
            "scheduled_at": scheduled_at,
            "platform": ",".join(platforms) if platforms else None,
            "is_holiday": False,
            "is_recurring": False,
            "created_by": user_id,
            "status": "ACTIVE",
        }
        event = await self._repo.create_event(event_data)
        logger.info(
            "calendar_content_event_created",
            content_id=str(content_id),
            event_id=str(event.id),
        )
        return event

    async def update_content_event(
        self,
        content_id: UUID,
        org_id: UUID,
        title: str | None = None,
        scheduled_at: datetime | None = None,
    ) -> CalendarEvent | None:
        """콘텐츠 예약 변경 시 캘린더 이벤트 업데이트."""
        event = await self._repo.find_by_content_id(content_id, org_id)
        if event is None:
            return None

        update_data: dict = {}
        if title is not None:
            update_data["title"] = title
        if scheduled_at is not None:
            update_data["scheduled_at"] = scheduled_at
            update_data["event_date"] = scheduled_at.date()

        if update_data:
            updated = await self._repo.update_event(event.id, org_id, update_data)
            logger.info(
                "calendar_content_event_updated",
                content_id=str(content_id),
                event_id=str(event.id),
            )
            return updated
        return event

    async def delete_content_events(self, content_id: UUID, org_id: UUID) -> int:
        """콘텐츠 삭제/취소 시 연결 이벤트 삭제."""
        count = await self._repo.delete_by_content_id(content_id, org_id)
        if count > 0:
            logger.info(
                "calendar_content_events_deleted",
                content_id=str(content_id),
                deleted_count=count,
            )
        return count
