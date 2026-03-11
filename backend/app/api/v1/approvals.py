"""Approvals API — 6 endpoints (S6, F09)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import WorkspaceContext, get_workspace_context, require_roles
from app.models.approval import ApprovalRequest, ApprovalWorkflow
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.approval_repository import ApprovalRepository
from app.repositories.content_repository import ContentRepository
from app.schemas.approval import (
    ApprovalActionRequest,
    ApprovalHistoryResponse,
    ApprovalRequestResponse,
    WorkflowResponse,
    WorkflowUpdateRequest,
)
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta
from app.services.approval_service import ApprovalService

router = APIRouter()


def _get_service(db: AsyncSession = Depends(get_db_session)) -> ApprovalService:
    return ApprovalService(ApprovalRepository(db), ContentRepository(db))


def _to_approval_response(r: ApprovalRequest) -> ApprovalRequestResponse:
    histories = []
    if hasattr(r, "histories") and r.histories:
        histories = [
            ApprovalHistoryResponse(
                id=str(h.id),
                request_id=str(h.request_id),
                step=h.step,
                action=h.action.value,
                reviewer_id=str(h.reviewer_id) if h.reviewer_id else None,
                comment=h.comment,
                created_at=h.created_at.isoformat(),
            )
            for h in r.histories
        ]
    return ApprovalRequestResponse(
        id=str(r.id),
        content_id=str(r.content_id),
        organization_id=str(r.organization_id),
        workflow_id=str(r.workflow_id) if r.workflow_id else None,
        current_step=r.current_step,
        status=r.status.value,
        requested_by=str(r.requested_by),
        requested_by_name=r.requester.name if hasattr(r, "requester") and r.requester else None,
        content_title=r.content.title if hasattr(r, "content") and r.content else None,
        platforms=list(r.content.platforms) if hasattr(r, "content") and r.content and r.content.platforms else [],
        is_urgent=r.is_urgent,
        comment=r.comment,
        histories=histories,
        created_at=r.created_at.isoformat(),
        updated_at=r.updated_at.isoformat(),
    )


def _to_workflow_response(w: ApprovalWorkflow) -> WorkflowResponse:
    return WorkflowResponse(
        id=str(w.id),
        organization_id=str(w.organization_id),
        name=w.name,
        steps=w.steps,
        is_active=w.is_active,
        created_at=w.created_at.isoformat(),
    )


# ── GET /workflows (before /{approval_id} to avoid route conflict) ──
@router.get("/workflows", response_model=ApiResponse[list[WorkflowResponse]])
async def get_workflows(
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ApprovalService = Depends(_get_service),
) -> dict:
    workflows = await service.get_workflows(workspace.org_id)
    return {"success": True, "data": [_to_workflow_response(w) for w in workflows]}


# ── PUT /workflows ──────────────────────────────────────
@router.put("/workflows", response_model=ApiResponse[WorkflowResponse])
async def update_workflow(
    body: WorkflowUpdateRequest,
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER)),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ApprovalService = Depends(_get_service),
) -> dict:
    wf = await service.update_workflow(workspace.org_id, body.model_dump(exclude_unset=True))
    return {"success": True, "data": _to_workflow_response(wf)}


# ── GET /approvals ──────────────────────────────────────
@router.get("", response_model=PaginatedResponse[ApprovalRequestResponse])
async def list_approvals(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    content_id: UUID | None = Query(None),
    requested_by: UUID | None = Query(None),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ApprovalService = Depends(_get_service),
) -> dict:
    requests, total = await service.list_approvals(
        workspace.org_id, page=page, limit=limit, status=status,
        content_id=content_id, requested_by=requested_by,
    )
    return {
        "success": True,
        "data": [_to_approval_response(r) for r in requests],
        "meta": PaginationMeta(total=total, page=page, limit=limit, total_pages=(total + limit - 1) // limit),
    }


# ── GET /approvals/:id ─────────────────────────────────
@router.get("/{approval_id}", response_model=ApiResponse[ApprovalRequestResponse])
async def get_approval(
    approval_id: UUID,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ApprovalService = Depends(_get_service),
) -> dict:
    req = await service.get_approval(approval_id, workspace.org_id)
    return {"success": True, "data": _to_approval_response(req)}


# ── POST /approvals/:id/approve ────────────────────────
@router.post("/{approval_id}/approve", response_model=ApiResponse[ApprovalRequestResponse])
async def approve(
    approval_id: UUID,
    body: ApprovalActionRequest,
    _user: User = Depends(require_roles(UserRole.CLIENT_DIRECTOR, UserRole.AGENCY_MANAGER)),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ApprovalService = Depends(_get_service),
) -> dict:
    req = await service.approve(approval_id, workspace.org_id, workspace.user.id, body.comment)
    return {"success": True, "data": _to_approval_response(req)}


# ── POST /approvals/:id/reject ─────────────────────────
@router.post("/{approval_id}/reject", response_model=ApiResponse[ApprovalRequestResponse])
async def reject(
    approval_id: UUID,
    body: ApprovalActionRequest,
    _user: User = Depends(require_roles(UserRole.CLIENT_DIRECTOR, UserRole.AGENCY_MANAGER)),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ApprovalService = Depends(_get_service),
) -> dict:
    req = await service.reject(approval_id, workspace.org_id, workspace.user.id, body.comment)
    return {"success": True, "data": _to_approval_response(req)}
