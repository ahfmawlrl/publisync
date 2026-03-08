"""Audit Logs API — 3 endpoints (S12, F14)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import WorkspaceContext, get_workspace_context, require_roles
from app.models.audit import AuditLog
from app.models.enums import UserRole
from app.repositories.audit_repository import AuditRepository
from app.schemas.audit import AuditLogResponse
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta
from app.services.audit_service import AuditService

router = APIRouter()


def _get_service(db: AsyncSession = Depends(get_db_session)) -> AuditService:
    return AuditService(AuditRepository(db))


def _to_response(log: AuditLog) -> AuditLogResponse:
    return AuditLogResponse(
        id=str(log.id),
        organization_id=str(log.organization_id),
        actor_id=str(log.actor_id) if log.actor_id else None,
        actor_name=log.actor.name if hasattr(log, "actor") and log.actor else None,
        actor_role=log.actor_role.value if log.actor_role else None,
        action=log.action.value,
        resource_type=log.resource_type,
        resource_id=str(log.resource_id) if log.resource_id else None,
        changes=log.changes,
        ip_address=log.ip_address,
        user_agent=log.user_agent,
        request_id=str(log.request_id) if log.request_id else None,
        created_at=str(log.created_at),
    )


# ── GET /audit-logs ────────────────────────────────────
@router.get("", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    action: str | None = Query(None),
    resource_type: str | None = Query(None),
    actor_id: str | None = Query(None),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user=Depends(require_roles(UserRole.SYSTEM_ADMIN, UserRole.AGENCY_MANAGER, UserRole.CLIENT_DIRECTOR)),
    service: AuditService = Depends(_get_service),
) -> dict:
    logs, total = await service.list_logs(
        workspace.org_id,
        page=page,
        limit=limit,
        action=action,
        resource_type=resource_type,
        actor_id=actor_id,
        start_date=start_date,
        end_date=end_date,
    )
    return {
        "success": True,
        "data": [_to_response(log) for log in logs],
        "meta": PaginationMeta(
            total=total, page=page, limit=limit, total_pages=(total + limit - 1) // limit
        ),
    }


# ── GET /audit-logs/export ─────────────────────────────
@router.get("/export")
async def export_audit_logs(
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    start_date: str = Query(...),
    end_date: str = Query(...),
    actions: str | None = Query(None, description="Comma-separated action filter"),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user=Depends(require_roles(UserRole.SYSTEM_ADMIN, UserRole.AGENCY_MANAGER)),
    service: AuditService = Depends(_get_service),
) -> StreamingResponse:
    action_list = [a.strip() for a in actions.split(",")] if actions else None
    csv_data = await service.export_logs(
        workspace.org_id, format=format, start_date=start_date, end_date=end_date, actions=action_list
    )
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=audit_logs_{start_date}_{end_date}.csv"},
    )


# ── GET /audit-logs/:id ───────────────────────────────
@router.get("/{log_id}", response_model=ApiResponse[AuditLogResponse])
async def get_audit_log(
    log_id: UUID,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user=Depends(require_roles(UserRole.SYSTEM_ADMIN, UserRole.AGENCY_MANAGER, UserRole.CLIENT_DIRECTOR)),
    service: AuditService = Depends(_get_service),
) -> dict:
    log = await service.get_log(log_id, workspace.org_id)
    return {"success": True, "data": _to_response(log)}
