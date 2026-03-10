"""Reply Templates API — 4 endpoints (S9, F04)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import WorkspaceContext, get_workspace_context, require_roles
from app.models.comment import ReplyTemplate
from app.models.enums import UserRole
from app.repositories.comment_repository import CommentRepository
from app.schemas.comment import (
    ReplyTemplateCreateRequest,
    ReplyTemplateResponse,
    ReplyTemplateUpdateRequest,
)
from app.schemas.common import ApiResponse
from app.services.comment_service import CommentService

router = APIRouter()


def _get_service(db: AsyncSession = Depends(get_db_session)) -> CommentService:
    return CommentService(CommentRepository(db))


def _to_template_response(t: ReplyTemplate) -> ReplyTemplateResponse:
    return ReplyTemplateResponse(
        id=str(t.id),
        organization_id=str(t.organization_id),
        category=t.category,
        name=t.name,
        content=t.content,
        variables=t.variables,
        usage_count=t.usage_count,
        is_active=t.is_active,
        created_by=str(t.created_by),
        created_at=t.created_at.isoformat(),
        updated_at=t.updated_at.isoformat(),
    )


# ── GET /reply-templates ─────────────────────────────────
@router.get("", response_model=ApiResponse[list[ReplyTemplateResponse]])
async def list_templates(
    category: str | None = Query(None),
    _user=Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: CommentService = Depends(_get_service),
) -> dict:
    templates = await service.list_templates(workspace.org_id, category=category)
    return {"success": True, "data": [_to_template_response(t) for t in templates]}


# ── POST /reply-templates ────────────────────────────────
@router.post(
    "",
    response_model=ApiResponse[ReplyTemplateResponse],
    status_code=201,
    dependencies=[Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR))],
)
async def create_template(
    body: ReplyTemplateCreateRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: CommentService = Depends(_get_service),
) -> dict:
    template = await service.create_template(
        workspace.org_id, workspace.user.id, body.model_dump()
    )
    return {"success": True, "data": _to_template_response(template)}


# ── PUT /reply-templates/:id ─────────────────────────────
@router.put(
    "/{template_id}",
    response_model=ApiResponse[ReplyTemplateResponse],
    dependencies=[Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR))],
)
async def update_template(
    template_id: UUID,
    body: ReplyTemplateUpdateRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: CommentService = Depends(_get_service),
) -> dict:
    template = await service.update_template(
        template_id, workspace.org_id, body.model_dump(exclude_unset=True)
    )
    return {"success": True, "data": _to_template_response(template)}


# ── DELETE /reply-templates/:id ──────────────────────────
@router.delete(
    "/{template_id}",
    status_code=204,
    dependencies=[Depends(require_roles(UserRole.AGENCY_MANAGER))],
)
async def delete_template(
    template_id: UUID,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: CommentService = Depends(_get_service),
) -> None:
    await service.delete_template(template_id, workspace.org_id)
