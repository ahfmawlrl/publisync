"""Media Library API — 10 endpoints (Phase 2, F11)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import WorkspaceContext, get_workspace_context, require_roles
from app.integrations.storage import (
    ALLOWED_CONTENT_TYPES,
    generate_presigned_upload_url,
)
from app.models.enums import UserRole
from app.models.media import MediaAsset, MediaFolder
from app.models.user import User
from app.repositories.media_repository import MediaRepository
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationMeta
from app.schemas.media import (
    MediaAssetListItem,
    MediaAssetResponse,
    MediaFolderCreateRequest,
    MediaFolderResponse,
    MediaUpdateRequest,
    MediaUploadRequest,
    PresignedUploadRequest,
    SubtitleUpdateRequest,
)
from app.services.media_service import MediaService

router = APIRouter()


def _get_service(db: AsyncSession = Depends(get_db_session)) -> MediaService:
    return MediaService(MediaRepository(db))


def _to_asset_response(a: MediaAsset) -> MediaAssetResponse:
    return MediaAssetResponse(
        id=str(a.id),
        organization_id=str(a.organization_id),
        filename=a.filename,
        original_filename=a.original_filename,
        mime_type=a.mime_type,
        media_type=a.media_type.value if hasattr(a.media_type, "value") else str(a.media_type),
        object_key=a.object_key,
        file_size=a.file_size,
        duration=a.duration,
        width=a.width,
        height=a.height,
        tags=a.tags or [],
        metadata=a.metadata_,
        folder_id=str(a.folder_id) if a.folder_id else None,
        version=a.version,
        created_by=str(a.created_by),
        created_at=a.created_at.isoformat(),
        updated_at=a.updated_at.isoformat(),
    )


def _to_asset_list_item(a: MediaAsset) -> MediaAssetListItem:
    return MediaAssetListItem(
        id=str(a.id),
        organization_id=str(a.organization_id),
        filename=a.filename,
        original_filename=a.original_filename,
        mime_type=a.mime_type,
        media_type=a.media_type.value if hasattr(a.media_type, "value") else str(a.media_type),
        object_key=a.object_key,
        file_size=a.file_size,
        duration=a.duration,
        width=a.width,
        height=a.height,
        tags=a.tags or [],
        folder_id=str(a.folder_id) if a.folder_id else None,
        version=a.version,
        created_by=str(a.created_by),
        created_at=a.created_at.isoformat(),
        updated_at=a.updated_at.isoformat(),
    )


def _to_folder_response(f: MediaFolder) -> MediaFolderResponse:
    return MediaFolderResponse(
        id=str(f.id),
        organization_id=str(f.organization_id),
        name=f.name,
        parent_id=str(f.parent_id) if f.parent_id else None,
        created_at=f.created_at.isoformat(),
    )


# ── GET /media ────────────────────────────────────────────
@router.get("", response_model=PaginatedResponse[MediaAssetListItem])
async def list_media(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    media_type: str | None = Query(None),
    folder_id: UUID | None = Query(None),
    search: str | None = Query(None),
    tags: list[str] | None = Query(None),
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)),
    service: MediaService = Depends(_get_service),
) -> dict:
    """List media assets with optional filtering."""
    assets, total = await service.list_assets(
        workspace.org_id,
        page=page,
        limit=limit,
        media_type=media_type,
        folder_id=folder_id,
        search=search,
        tags=tags,
    )
    return {
        "success": True,
        "data": [_to_asset_list_item(a) for a in assets],
        "meta": PaginationMeta(
            total=total, page=page, limit=limit, total_pages=(total + limit - 1) // limit
        ),
    }


# ── POST /media/upload ────────────────────────────────────
@router.post("/upload", response_model=ApiResponse[MediaAssetResponse], status_code=201)
async def create_media_record(
    body: MediaUploadRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)),
    service: MediaService = Depends(_get_service),
) -> dict:
    """Create a media asset record after the file has been uploaded to storage."""
    asset = await service.create_asset_record(
        workspace.org_id,
        workspace.user.id,
        body.model_dump(),
    )
    return {"success": True, "data": _to_asset_response(asset)}


# ── GET /media/folders ────────────────────────────────────
@router.get("/folders", response_model=ApiResponse[list[MediaFolderResponse]])
async def list_folders(
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)),
    service: MediaService = Depends(_get_service),
) -> dict:
    """List all media folders for the organization."""
    folders = await service.list_folders(workspace.org_id)
    return {"success": True, "data": [_to_folder_response(f) for f in folders]}


# ── POST /media/folders ───────────────────────────────────
@router.post("/folders", response_model=ApiResponse[MediaFolderResponse], status_code=201)
async def create_folder(
    body: MediaFolderCreateRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER)),
    service: MediaService = Depends(_get_service),
) -> dict:
    """Create a new media folder."""
    parent_id = UUID(body.parent_id) if body.parent_id else None
    folder = await service.create_folder(workspace.org_id, body.name, parent_id)
    return {"success": True, "data": _to_folder_response(folder)}


# ── POST /media/presigned-upload ──────────────────────────
@router.post("/presigned-upload", response_model=dict)
async def get_presigned_upload_url(
    body: PresignedUploadRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
) -> dict:
    """Generate a presigned PUT URL for direct client-side upload to MinIO."""
    if body.content_type not in ALLOWED_CONTENT_TYPES:
        return {
            "success": False,
            "error": {
                "code": "INVALID_CONTENT_TYPE",
                "message": f"지원하지 않는 파일 형식입니다. 허용: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}",
            },
        }

    result = generate_presigned_upload_url(
        org_id=str(workspace.org_id),
        filename=body.filename,
        content_type=body.content_type,
    )

    return {
        "success": True,
        "data": result,
    }


# ── GET /media/{asset_id} ────────────────────────────────
@router.get("/{asset_id}", response_model=ApiResponse[MediaAssetResponse])
async def get_media_asset(
    asset_id: UUID,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)),
    service: MediaService = Depends(_get_service),
) -> dict:
    """Get a single media asset by ID."""
    asset = await service.get_asset(asset_id, workspace.org_id)
    return {"success": True, "data": _to_asset_response(asset)}


# ── PUT /media/{asset_id} ────────────────────────────────
@router.put("/{asset_id}", response_model=ApiResponse[MediaAssetResponse])
async def update_media_asset(
    asset_id: UUID,
    body: MediaUpdateRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)),
    service: MediaService = Depends(_get_service),
) -> dict:
    """Update media asset metadata (filename, tags, folder)."""
    asset = await service.update_asset(
        asset_id, workspace.org_id, body.model_dump(exclude_unset=True)
    )
    return {"success": True, "data": _to_asset_response(asset)}


# ── PUT /media/{asset_id}/subtitles ──────────────────────
@router.put("/{asset_id}/subtitles", response_model=ApiResponse[MediaAssetResponse])
async def update_media_subtitles(
    asset_id: UUID,
    body: SubtitleUpdateRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)),
    service: MediaService = Depends(_get_service),
) -> dict:
    """Save subtitle data to a media asset's metadata."""
    subtitles_data = [s.model_dump() for s in body.subtitles]
    asset = await service.update_subtitles(
        asset_id, workspace.org_id, subtitles_data, body.language
    )
    return {"success": True, "data": _to_asset_response(asset)}


# ── DELETE /media/{asset_id} ─────────────────────────────
@router.delete("/{asset_id}", status_code=204)
async def delete_media_asset(
    asset_id: UUID,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER)),
    service: MediaService = Depends(_get_service),
) -> None:
    """Soft delete a media asset."""
    await service.delete_asset(asset_id, workspace.org_id)


# ── GET /media/{asset_id}/download ─────────────────────
@router.get("/{asset_id}/download")
async def download_media_asset(
    asset_id: UUID,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)),
    service: MediaService = Depends(_get_service),
):
    """Stream the original media file from MinIO storage."""
    asset = await service.get_asset(asset_id, workspace.org_id)

    try:
        from app.core.config import settings
        from app.integrations.storage import get_minio_client

        minio_client = get_minio_client()
        response = minio_client.get_object(settings.MINIO_BUCKET, asset.object_key)
        return StreamingResponse(
            response.stream(32 * 1024),
            media_type=asset.mime_type or "application/octet-stream",
            headers={
                "Content-Disposition": f'inline; filename="{asset.original_filename or asset.filename}"',
            },
        )
    except Exception:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": {
                    "code": "FILE_NOT_FOUND",
                    "message": "파일을 불러올 수 없습니다.",
                },
            },
        )


# ── GET /media/{asset_id}/thumbnail ────────────────────
@router.get("/{asset_id}/thumbnail")
async def get_media_thumbnail(
    asset_id: UUID,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)),
    service: MediaService = Depends(_get_service),
):
    """Stream the thumbnail image for a media asset. Falls back to original for images."""
    asset = await service.get_asset(asset_id, workspace.org_id)
    thumbnail_key = asset.thumbnail_url or (
        asset.object_key if asset.mime_type and asset.mime_type.startswith("image/") else None
    )

    if not thumbnail_key:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": {
                    "code": "THUMBNAIL_NOT_FOUND",
                    "message": "썸네일이 존재하지 않습니다.",
                },
            },
        )

    try:
        from app.core.config import settings
        from app.integrations.storage import get_minio_client

        minio_client = get_minio_client()
        response = minio_client.get_object(settings.MINIO_BUCKET, thumbnail_key)
        return StreamingResponse(
            response.stream(32 * 1024),
            media_type="image/jpeg",
        )
    except Exception:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": {
                    "code": "THUMBNAIL_NOT_FOUND",
                    "message": "썸네일을 불러올 수 없습니다.",
                },
            },
        )
