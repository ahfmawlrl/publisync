"""Comments API — 8 endpoints (S9, F04)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import WorkspaceContext, get_workspace_context, require_roles
from app.models.comment import Comment
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.comment_repository import CommentRepository
from app.schemas.comment import (
    CommentDeleteRequest,
    CommentHideRequest,
    CommentReplyRequest,
    CommentResponse,
    DangerousCommentResponse,
)
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta
from app.services.comment_service import CommentService

router = APIRouter()


def _get_service(db: AsyncSession = Depends(get_db_session)) -> CommentService:
    return CommentService(CommentRepository(db))


def _to_comment_response(c: Comment) -> CommentResponse:
    return CommentResponse(
        id=str(c.id),
        organization_id=str(c.organization_id),
        content_id=str(c.content_id) if c.content_id else None,
        channel_id=str(c.channel_id),
        platform=c.platform.value,
        external_id=c.external_id,
        text=c.text,
        author_name=c.author_name,
        author_profile_url=c.author_profile_url,
        parent_comment_id=str(c.parent_comment_id) if c.parent_comment_id else None,
        sentiment=c.sentiment.value if c.sentiment else None,
        sentiment_confidence=c.sentiment_confidence,
        dangerous_level=c.dangerous_level,
        keywords=c.keywords,
        status=c.status.value,
        reply_text=c.reply_text,
        reply_draft=c.reply_draft,
        replied_at=c.replied_at.isoformat() if c.replied_at else None,
        hidden_reason=c.hidden_reason,
        delete_reason=c.delete_reason,
        processed_by=str(c.processed_by) if c.processed_by else None,
        platform_created_at=c.platform_created_at.isoformat() if c.platform_created_at else None,
        created_at=c.created_at.isoformat(),
        updated_at=c.updated_at.isoformat(),
    )


def _to_dangerous_response(c: Comment) -> DangerousCommentResponse:
    return DangerousCommentResponse(
        id=str(c.id),
        organization_id=str(c.organization_id),
        content_id=str(c.content_id) if c.content_id else None,
        channel_id=str(c.channel_id),
        platform=c.platform.value,
        external_id=c.external_id,
        text=c.text,
        author_name=c.author_name,
        author_profile_url=c.author_profile_url,
        parent_comment_id=str(c.parent_comment_id) if c.parent_comment_id else None,
        sentiment=c.sentiment.value if c.sentiment else None,
        sentiment_confidence=c.sentiment_confidence,
        dangerous_level=c.dangerous_level,
        keywords=c.keywords,
        status=c.status.value,
        reply_text=c.reply_text,
        reply_draft=c.reply_draft,
        replied_at=c.replied_at.isoformat() if c.replied_at else None,
        hidden_reason=c.hidden_reason,
        delete_reason=c.delete_reason,
        processed_by=str(c.processed_by) if c.processed_by else None,
        platform_created_at=c.platform_created_at.isoformat() if c.platform_created_at else None,
        created_at=c.created_at.isoformat(),
        updated_at=c.updated_at.isoformat(),
    )


# ── GET /comments ────────────────────────────────────────
@router.get("", response_model=PaginatedResponse[CommentResponse])
async def list_comments(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    platform: str | None = Query(None),
    channel_id: str | None = Query(None),
    search: str | None = Query(None),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: CommentService = Depends(_get_service),
) -> dict:
    channel_uuid = UUID(channel_id) if channel_id else None
    comments, total = await service.list_comments(
        workspace.org_id,
        page=page,
        limit=limit,
        status=status,
        platform=platform,
        channel_id=channel_uuid,
        search=search,
    )
    return {
        "success": True,
        "data": [_to_comment_response(c) for c in comments],
        "meta": PaginationMeta(
            total=total, page=page, limit=limit, total_pages=(total + limit - 1) // limit
        ),
    }


# ── GET /comments/dangerous ─────────────────────────────
@router.get("/dangerous", response_model=PaginatedResponse[DangerousCommentResponse])
async def list_dangerous_comments(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: CommentService = Depends(_get_service),
) -> dict:
    comments, total = await service.get_dangerous_comments(
        workspace.org_id, page=page, limit=limit
    )
    return {
        "success": True,
        "data": [_to_dangerous_response(c) for c in comments],
        "meta": PaginationMeta(
            total=total, page=page, limit=limit, total_pages=(total + limit - 1) // limit
        ),
    }


# ── GET /comments/:id ───────────────────────────────────
@router.get("/{comment_id}", response_model=ApiResponse[CommentResponse])
async def get_comment(
    comment_id: UUID,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: CommentService = Depends(_get_service),
) -> dict:
    comment = await service.get_comment(comment_id, workspace.org_id)
    return {"success": True, "data": _to_comment_response(comment)}


# ── POST /comments/:id/reply ────────────────────────────
@router.post(
    "/{comment_id}/reply",
    response_model=ApiResponse[CommentResponse],
    dependencies=[Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR))],
)
async def reply_comment(
    comment_id: UUID,
    body: CommentReplyRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: CommentService = Depends(_get_service),
) -> dict:
    comment = await service.reply_comment(
        comment_id, workspace.org_id, workspace.user.id, body.text
    )
    return {"success": True, "data": _to_comment_response(comment)}


# ── POST /comments/:id/hide ─────────────────────────────
@router.post(
    "/{comment_id}/hide",
    response_model=ApiResponse[CommentResponse],
    dependencies=[Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR))],
)
async def hide_comment(
    comment_id: UUID,
    body: CommentHideRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: CommentService = Depends(_get_service),
) -> dict:
    comment = await service.hide_comment(
        comment_id, workspace.org_id, workspace.user.id, body.reason
    )
    return {"success": True, "data": _to_comment_response(comment)}


# ── POST /comments/:id/delete-request ───────────────────
@router.post(
    "/{comment_id}/delete-request",
    response_model=ApiResponse[CommentResponse],
    dependencies=[Depends(require_roles(UserRole.AGENCY_OPERATOR))],
)
async def request_delete(
    comment_id: UUID,
    body: CommentDeleteRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: CommentService = Depends(_get_service),
) -> dict:
    comment = await service.request_delete(
        comment_id, workspace.org_id, workspace.user.id, body.reason
    )
    return {"success": True, "data": _to_comment_response(comment)}


# ── POST /comments/:id/ignore ───────────────────────────
@router.post(
    "/{comment_id}/ignore",
    response_model=ApiResponse[CommentResponse],
    dependencies=[Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.CLIENT_DIRECTOR))],
)
async def ignore_dangerous(
    comment_id: UUID,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: CommentService = Depends(_get_service),
) -> dict:
    comment = await service.ignore_dangerous(
        comment_id, workspace.org_id, workspace.user.id
    )
    return {"success": True, "data": _to_comment_response(comment)}


# ── POST /comments/:id/delete-approve ───────────────────
@router.post(
    "/{comment_id}/delete-approve",
    response_model=ApiResponse[CommentResponse],
    dependencies=[Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.CLIENT_DIRECTOR))],
)
async def approve_delete(
    comment_id: UUID,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: CommentService = Depends(_get_service),
) -> dict:
    comment = await service.approve_delete(
        comment_id, workspace.org_id, workspace.user.id
    )
    return {"success": True, "data": _to_comment_response(comment)}
