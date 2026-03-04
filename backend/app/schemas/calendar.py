"""Pydantic schemas for Calendar endpoints — S16 (F10, Phase 2)."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class CalendarEventResponse(BaseModel):
    id: str
    organization_id: str
    content_id: str | None = None
    event_type: str
    title: str
    description: str | None = None
    event_date: str
    scheduled_at: str | None = None
    platform: str | None = None
    status: str
    is_holiday: bool
    is_recurring: bool
    color: str | None = None
    created_by: str | None = None
    created_at: str
    updated_at: str


class CalendarEventCreateRequest(BaseModel):
    event_type: str = Field("CUSTOM")
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    event_date: date
    scheduled_at: datetime | None = None
    platform: str | None = None
    is_holiday: bool = False
    is_recurring: bool = False
    color: str | None = None


class CalendarRescheduleRequest(BaseModel):
    event_date: date
    scheduled_at: datetime | None = None


class HolidayUpdateRequest(BaseModel):
    holidays: list[CalendarEventCreateRequest]
