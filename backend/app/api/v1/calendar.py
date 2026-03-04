"""Calendar API — 4 endpoints (S16, F10, Phase 2)."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import WorkspaceContext, get_workspace_context, require_roles
from app.models.calendar import CalendarEvent
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.calendar_repository import CalendarRepository
from app.schemas.calendar import (
    CalendarEventResponse,
    CalendarRescheduleRequest,
    HolidayUpdateRequest,
)
from app.schemas.common import ApiResponse
from app.services.calendar_service import CalendarService

router = APIRouter()


def _get_service(db: AsyncSession = Depends(get_db_session)) -> CalendarService:
    return CalendarService(CalendarRepository(db))


def _to_event_response(e: CalendarEvent) -> CalendarEventResponse:
    return CalendarEventResponse(
        id=str(e.id),
        organization_id=str(e.organization_id),
        content_id=str(e.content_id) if e.content_id else None,
        event_type=e.event_type.value if hasattr(e.event_type, "value") else str(e.event_type),
        title=e.title,
        description=e.description,
        event_date=e.event_date.isoformat(),
        scheduled_at=e.scheduled_at.isoformat() if e.scheduled_at else None,
        platform=e.platform,
        status=e.status,
        is_holiday=e.is_holiday,
        is_recurring=e.is_recurring,
        color=e.color,
        created_by=str(e.created_by) if e.created_by else None,
        created_at=e.created_at.isoformat(),
        updated_at=e.updated_at.isoformat(),
    )


# -- GET /calendar/events ------------------------------------------------
@router.get("/events", response_model=ApiResponse[list[CalendarEventResponse]])
async def list_events(
    start_date: date = Query(..., description="조회 시작 날짜 (YYYY-MM-DD)"),
    end_date: date = Query(..., description="조회 종료 날짜 (YYYY-MM-DD)"),
    event_type: str | None = Query(None, description="이벤트 타입 필터"),
    _user: User = Depends(
        require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR, UserRole.CLIENT_DIRECTOR)
    ),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: CalendarService = Depends(_get_service),
) -> dict:
    events = await service.list_events(
        workspace.org_id, start_date, end_date, event_type
    )
    return {
        "success": True,
        "data": [_to_event_response(e) for e in events],
    }


# -- PATCH /calendar/events/:id/reschedule -------------------------------
@router.patch(
    "/events/{event_id}/reschedule",
    response_model=ApiResponse[CalendarEventResponse],
)
async def reschedule_event(
    event_id: UUID,
    body: CalendarRescheduleRequest,
    _user: User = Depends(
        require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)
    ),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: CalendarService = Depends(_get_service),
) -> dict:
    event, conflict = await service.reschedule_event(
        event_id, workspace.org_id, body.event_date, body.scheduled_at
    )
    meta = {"conflict": conflict} if conflict else None
    return {
        "success": True,
        "data": _to_event_response(event),
        "meta": meta,
    }


# -- GET /calendar/holidays ----------------------------------------------
@router.get("/holidays", response_model=ApiResponse[list[CalendarEventResponse]])
async def get_holidays(
    year: int = Query(..., ge=2000, le=2100, description="조회 연도"),
    _user: User = Depends(
        require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR, UserRole.CLIENT_DIRECTOR)
    ),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: CalendarService = Depends(_get_service),
) -> dict:
    holidays = await service.get_holidays(workspace.org_id, year)
    return {
        "success": True,
        "data": [_to_event_response(e) for e in holidays],
    }


# -- PUT /calendar/holidays -----------------------------------------------
@router.put("/holidays", response_model=ApiResponse[list[CalendarEventResponse]])
async def update_holidays(
    body: HolidayUpdateRequest,
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER)),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: CalendarService = Depends(_get_service),
) -> dict:
    holidays_data = [h.model_dump() for h in body.holidays]
    created = await service.update_holidays(
        workspace.org_id, holidays_data, workspace.user.id
    )
    return {
        "success": True,
        "data": [_to_event_response(e) for e in created],
    }
