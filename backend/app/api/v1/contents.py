"""Contents API — 17 endpoints (S5, F01, v2.0 +6 variants)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import WorkspaceContext, get_workspace_context
from app.models.content import Content, ContentVariant, PublishResult, VariantMedia
from app.repositories.approval_repository import ApprovalRepository
from app.repositories.content_repository import ContentRepository
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta
from app.schemas.content import (
    BulkActionRequest,
    ContentCreateRequest,
    ContentResponse,
    ContentUpdateRequest,
    PublishResultResponse,
    VariantCreateRequest,
    VariantMediaAttachRequest,
    VariantMediaResponse,
    VariantResponse,
    VariantUpdateRequest,
)
from app.services.content_service import ContentService

router = APIRouter()


def _get_service(db: AsyncSession = Depends(get_db_session)) -> ContentService:
    return ContentService(
        ContentRepository(db),
        approval_repo=ApprovalRepository(db),
    )


def _to_variant_media_response(vm: VariantMedia) -> VariantMediaResponse:
    return VariantMediaResponse(
        id=str(vm.id),
        media_asset_id=str(vm.media_asset_id),
        role=vm.role.value if hasattr(vm.role, "value") else str(vm.role),
        sort_order=vm.sort_order,
        metadata=vm.metadata_,
        created_at=vm.created_at.isoformat(),
    )


def _to_variant_response(v: ContentVariant) -> VariantResponse:
    return VariantResponse(
        id=str(v.id),
        content_id=str(v.content_id),
        organization_id=str(v.organization_id),
        platform=v.platform.value if hasattr(v.platform, "value") else str(v.platform),
        channel_id=str(v.channel_id) if v.channel_id else None,
        title=v.title,
        body=v.body,
        hashtags=v.hashtags or [],
        metadata=v.metadata_,
        sort_order=v.sort_order,
        media=[_to_variant_media_response(vm) for vm in (v.media or [])],
        created_at=v.created_at.isoformat(),
        updated_at=v.updated_at.isoformat(),
    )


def _to_content_response(c: Content) -> ContentResponse:
    meta = c.metadata_ or {}
    return ContentResponse(
        id=str(c.id),
        organization_id=str(c.organization_id),
        title=c.title,
        body=c.body,
        status=c.status.value,
        platforms=c.platforms or [],
        channel_ids=[str(cid) for cid in (c.channel_ids or [])],
        scheduled_at=c.scheduled_at.isoformat() if c.scheduled_at else None,
        author_id=str(c.author_id),
        author_name=c.author.name if hasattr(c, "author") and c.author else None,
        platform_contents=c.platform_contents,
        metadata=c.metadata_,
        hashtags=meta.get("hashtags", []),
        ai_generated=c.ai_generated,
        media_urls=c.media_urls or [],
        source_media_id=str(c.source_media_id) if c.source_media_id else None,
        variants=[_to_variant_response(v) for v in (c.variants or [])],
        created_at=c.created_at.isoformat(),
        updated_at=c.updated_at.isoformat(),
    )


def _to_publish_result_response(pr: PublishResult) -> PublishResultResponse:
    return PublishResultResponse(
        id=str(pr.id),
        content_id=str(pr.content_id),
        variant_id=str(pr.variant_id) if pr.variant_id else None,
        channel_id=str(pr.channel_id),
        status=pr.status.value,
        platform_post_id=pr.platform_post_id,
        platform_url=pr.platform_url,
        error_message=pr.error_message,
        retry_count=pr.retry_count,
        views=pr.views,
        likes=pr.likes,
        shares=pr.shares,
        comments_count=pr.comments_count,
        created_at=pr.created_at.isoformat(),
    )


# ── POST /contents ──────────────────────────────────────
@router.post("", response_model=ApiResponse[ContentResponse], status_code=201)
async def create_content(
    body: ContentCreateRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ContentService = Depends(_get_service),
) -> dict:
    content = await service.create_content(
        workspace.org_id, workspace.user.id, body.model_dump()
    )
    return {"success": True, "data": _to_content_response(content)}


# ── GET /contents ───────────────────────────────────────
@router.get("", response_model=PaginatedResponse[ContentResponse])
async def list_contents(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    platform: str | None = Query(None),
    search: str | None = Query(None),
    period: str | None = Query(None, pattern=r"^(7d|30d|90d)$"),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ContentService = Depends(_get_service),
) -> dict:
    contents, total = await service.list_contents(
        workspace.org_id, page=page, limit=limit, status=status, platform=platform, search=search, period=period
    )
    return {
        "success": True,
        "data": [_to_content_response(c) for c in contents],
        "meta": PaginationMeta(total=total, page=page, limit=limit, total_pages=(total + limit - 1) // limit),
    }


# ── GET /contents/:id ──────────────────────────────────
@router.get("/{content_id}", response_model=ApiResponse[ContentResponse])
async def get_content(
    content_id: UUID,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ContentService = Depends(_get_service),
) -> dict:
    content = await service.get_content(content_id, workspace.org_id)
    return {"success": True, "data": _to_content_response(content)}


# ── PUT /contents/:id ──────────────────────────────────
@router.put("/{content_id}", response_model=ApiResponse[ContentResponse])
async def update_content(
    content_id: UUID,
    body: ContentUpdateRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ContentService = Depends(_get_service),
) -> dict:
    content = await service.update_content(
        content_id, workspace.org_id, workspace.user.id, body.model_dump(exclude_unset=True)
    )
    return {"success": True, "data": _to_content_response(content)}


# ── DELETE /contents/:id ───────────────────────────────
@router.delete("/{content_id}", status_code=204)
async def delete_content(
    content_id: UUID,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ContentService = Depends(_get_service),
) -> None:
    await service.delete_content(content_id, workspace.org_id)


# ── POST /contents/:id/save-draft ─────────────────────
@router.post("/{content_id}/save-draft", response_model=ApiResponse[ContentResponse])
async def save_draft(
    content_id: UUID,
    body: ContentUpdateRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ContentService = Depends(_get_service),
) -> dict:
    content = await service.save_draft(
        content_id, workspace.org_id, workspace.user.id, body.model_dump(exclude_unset=True)
    )
    return {"success": True, "data": _to_content_response(content)}


# ── POST /contents/:id/request-review ─────────────────
@router.post("/{content_id}/request-review", response_model=ApiResponse[ContentResponse])
async def request_review(
    content_id: UUID,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ContentService = Depends(_get_service),
) -> dict:
    content = await service.request_review(content_id, workspace.org_id, requester_id=workspace.user.id)
    return {"success": True, "data": _to_content_response(content)}


# ── GET /contents/:id/publish-history ─────────────────
@router.get("/{content_id}/publish-history", response_model=PaginatedResponse[PublishResultResponse])
async def get_publish_history(
    content_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ContentService = Depends(_get_service),
) -> dict:
    results, total = await service.get_publish_history(
        content_id, workspace.org_id, page=page, limit=limit
    )
    return {
        "success": True,
        "data": [_to_publish_result_response(pr) for pr in results],
        "meta": PaginationMeta(total=total, page=page, limit=limit, total_pages=(total + limit - 1) // limit),
    }


# ── POST /contents/:id/publish ────────────────────────
@router.post("/{content_id}/publish", response_model=ApiResponse[ContentResponse])
async def publish_content(
    content_id: UUID,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ContentService = Depends(_get_service),
) -> dict:
    content = await service.publish(content_id, workspace.org_id)
    return {"success": True, "data": _to_content_response(content)}


# ── POST /contents/:id/retry-publish ─────────────────
@router.post("/{content_id}/retry-publish", response_model=ApiResponse[ContentResponse])
async def retry_publish(
    content_id: UUID,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ContentService = Depends(_get_service),
) -> dict:
    content = await service.retry_publish(content_id, workspace.org_id)
    return {"success": True, "data": _to_content_response(content)}


# ── POST /contents/bulk-action ────────────────────────
@router.post("/bulk-action", response_model=ApiResponse[dict])
async def bulk_action(
    body: BulkActionRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ContentService = Depends(_get_service),
) -> dict:
    content_ids = [UUID(cid) for cid in body.content_ids]
    count = await service.bulk_action(workspace.org_id, content_ids, body.action)
    return {"success": True, "data": {"affected": count}}


# ── POST /contents/:id/cancel-publish ─────────────────
@router.post("/{content_id}/cancel-publish", response_model=ApiResponse[ContentResponse])
async def cancel_publish(
    content_id: UUID,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ContentService = Depends(_get_service),
) -> dict:
    content = await service.cancel_publish(content_id, workspace.org_id)
    return {"success": True, "data": _to_content_response(content)}


# ── v2.0: Variant endpoints ──────────────────────────────


# ── POST /contents/:id/variants ──────────────────────
@router.post("/{content_id}/variants", response_model=ApiResponse[VariantResponse], status_code=201)
async def create_variant(
    content_id: UUID,
    body: VariantCreateRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ContentService = Depends(_get_service),
) -> dict:
    variant = await service.create_variant(content_id, workspace.org_id, body.model_dump())
    return {"success": True, "data": _to_variant_response(variant)}


# ── GET /contents/:id/variants ───────────────────────
@router.get("/{content_id}/variants", response_model=ApiResponse[list[VariantResponse]])
async def list_variants(
    content_id: UUID,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ContentService = Depends(_get_service),
) -> dict:
    variants = await service.list_variants(content_id, workspace.org_id)
    return {"success": True, "data": [_to_variant_response(v) for v in variants]}


# ── PUT /contents/:id/variants/:vid ──────────────────
@router.put("/{content_id}/variants/{variant_id}", response_model=ApiResponse[VariantResponse])
async def update_variant(
    content_id: UUID,
    variant_id: UUID,
    body: VariantUpdateRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ContentService = Depends(_get_service),
) -> dict:
    variant = await service.update_variant(
        content_id, variant_id, workspace.org_id, body.model_dump(exclude_unset=True),
    )
    return {"success": True, "data": _to_variant_response(variant)}


# ── DELETE /contents/:id/variants/:vid ───────────────
@router.delete("/{content_id}/variants/{variant_id}", status_code=204)
async def delete_variant(
    content_id: UUID,
    variant_id: UUID,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ContentService = Depends(_get_service),
) -> None:
    await service.delete_variant(content_id, variant_id, workspace.org_id)


# ── POST /contents/:id/variants/:vid/media ───────────
@router.post(
    "/{content_id}/variants/{variant_id}/media",
    response_model=ApiResponse[VariantMediaResponse],
    status_code=201,
)
async def attach_variant_media(
    content_id: UUID,
    variant_id: UUID,
    body: VariantMediaAttachRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ContentService = Depends(_get_service),
) -> dict:
    vm = await service.attach_variant_media(
        content_id, variant_id, workspace.org_id, body.model_dump(),
    )
    return {"success": True, "data": _to_variant_media_response(vm)}


# ── DELETE /contents/:id/variants/:vid/media/:mid ────
@router.delete("/{content_id}/variants/{variant_id}/media/{media_id}", status_code=204)
async def detach_variant_media(
    content_id: UUID,
    variant_id: UUID,
    media_id: UUID,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    service: ContentService = Depends(_get_service),
) -> None:
    await service.detach_variant_media(content_id, variant_id, media_id, workspace.org_id)
