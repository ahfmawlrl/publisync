"""Media Library business logic — Phase 2 (F11)."""

from uuid import UUID

import structlog

from app.core.exceptions import NotFoundError, ValidationError
from app.integrations.storage import (
    ALLOWED_CONTENT_TYPES,
    generate_thumbnail,
    generate_video_thumbnail,
    get_video_metadata,
)
from app.models.media import MediaAsset, MediaFolder
from app.repositories.media_repository import MediaRepository

logger = structlog.get_logger()


def _index_media_to_search(asset: MediaAsset) -> None:
    """Index/update a media asset in Meilisearch (best-effort)."""
    try:
        from app.integrations.search import index_document

        doc = {
            "id": str(asset.id),
            "organization_id": str(asset.organization_id),
            "file_name": asset.filename or "",
            "original_name": asset.original_filename or "",
            "tags": asset.tags or [],
            "media_type": asset.media_type if isinstance(asset.media_type, str) else (
                asset.media_type.value if hasattr(asset.media_type, "value") else str(asset.media_type)
            ),
            "folder_id": str(asset.folder_id) if asset.folder_id else None,
            "created_at": asset.created_at.isoformat() if asset.created_at else "",
            "file_size": asset.file_size or 0,
        }
        index_document("media_assets", doc)
    except Exception as exc:
        logger.warning("search_index_media_failed", error=str(exc))


def _delete_media_from_search(asset_id: UUID) -> None:
    """Remove a media asset from Meilisearch (best-effort)."""
    try:
        from app.integrations.search import delete_document

        delete_document("media_assets", str(asset_id))
    except Exception as exc:
        logger.warning("search_delete_media_failed", error=str(exc))


# Map MIME type prefix to MediaType enum value
_MIME_TO_MEDIA_TYPE: dict[str, str] = {
    "image": "IMAGE",
    "video": "VIDEO",
    "audio": "AUDIO",
    "application": "DOCUMENT",
}

# 기관별 스토리지 제한 (50 GB)
STORAGE_QUOTA_BYTES: int = 50 * 1024 * 1024 * 1024
STORAGE_QUOTA_WARNING_RATIO: float = 0.80  # 80% — 경고
STORAGE_QUOTA_BLOCK_RATIO: float = 0.95    # 95% — 업로드 차단


class MediaNotFoundError(NotFoundError):
    detail = "Media asset not found"


class MediaService:
    def __init__(self, repo: MediaRepository) -> None:
        self._repo = repo

    async def list_assets(
        self,
        org_id: UUID,
        page: int = 1,
        limit: int = 20,
        media_type: str | None = None,
        folder_id: UUID | None = None,
        search: str | None = None,
        tags: list[str] | None = None,
    ) -> tuple[list[MediaAsset], int]:
        offset = (page - 1) * limit
        return await self._repo.list_assets(
            org_id,
            offset=offset,
            limit=limit,
            media_type=media_type,
            folder_id=folder_id,
            search=search,
            tags=tags,
        )

    async def get_asset(self, asset_id: UUID, org_id: UUID) -> MediaAsset:
        asset = await self._repo.get_asset(asset_id, org_id)
        if asset is None:
            raise MediaNotFoundError()
        return asset

    async def check_storage_quota(self, org_id: UUID) -> dict:
        """기관별 스토리지 사용량 및 잔여 용량 확인.

        Returns:
            dict with usage_bytes, quota_bytes, usage_ratio, warning, blocked.
        """
        usage = await self._repo.get_org_storage_usage(org_id)
        ratio = usage / STORAGE_QUOTA_BYTES if STORAGE_QUOTA_BYTES > 0 else 0.0
        warning = ratio >= STORAGE_QUOTA_WARNING_RATIO
        blocked = ratio >= STORAGE_QUOTA_BLOCK_RATIO

        if warning:
            logger.warning(
                "storage_quota_warning",
                org_id=str(org_id),
                usage_bytes=usage,
                quota_bytes=STORAGE_QUOTA_BYTES,
                usage_ratio=round(ratio * 100, 1),
            )

        return {
            "usage_bytes": usage,
            "quota_bytes": STORAGE_QUOTA_BYTES,
            "usage_ratio": round(ratio, 4),
            "warning": warning,
            "blocked": blocked,
        }

    async def create_asset_record(
        self, org_id: UUID, user_id: UUID, upload_data: dict
    ) -> MediaAsset:
        content_type = upload_data.get("content_type", "")
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise ValidationError(f"지원하지 않는 파일 형식입니다: {content_type}")

        # 스토리지 용량 확인 — 95% 이상이면 업로드 차단
        quota_info = await self.check_storage_quota(org_id)
        if quota_info["blocked"]:
            raise ValidationError(
                f"스토리지 용량이 부족합니다. "
                f"현재 사용량: {quota_info['usage_bytes'] / (1024**3):.1f}GB / "
                f"{STORAGE_QUOTA_BYTES / (1024**3):.0f}GB "
                f"({quota_info['usage_ratio'] * 100:.1f}%)"
            )

        # Determine media_type from MIME type
        mime_prefix = content_type.split("/")[0]
        media_type = _MIME_TO_MEDIA_TYPE.get(mime_prefix, "DOCUMENT")

        folder_id = None
        if upload_data.get("folder_id"):
            folder_id = (
                UUID(upload_data["folder_id"])
                if isinstance(upload_data["folder_id"], str)
                else upload_data["folder_id"]
            )

        asset_data = {
            "organization_id": org_id,
            "filename": upload_data["filename"],
            "original_filename": upload_data["original_filename"],
            "mime_type": content_type,
            "media_type": media_type,
            "object_key": upload_data["object_key"],
            "file_size": upload_data["file_size"],
            "duration": upload_data.get("duration"),
            "width": upload_data.get("width"),
            "height": upload_data.get("height"),
            "tags": upload_data.get("tags", []),
            "metadata_": upload_data.get("metadata"),
            "folder_id": folder_id,
            "created_by": user_id,
        }

        asset = await self._repo.create_asset(asset_data)
        logger.info("media_asset_created", asset_id=str(asset.id), filename=asset.filename)

        # 이미지인 경우 썸네일 자동 생성
        if media_type == "IMAGE":
            thumb_key = generate_thumbnail(
                org_id=str(org_id),
                object_key=upload_data["object_key"],
            )
            if thumb_key:
                asset = await self._repo.update_asset(
                    asset.id, org_id, {"thumbnail_url": thumb_key}
                )
                logger.info(
                    "media_thumbnail_set",
                    asset_id=str(asset.id),
                    thumb_key=thumb_key,
                )

        # 비디오인 경우 썸네일 + 메타데이터 추출
        elif media_type == "VIDEO":
            vid_update: dict = {}

            # 비디오 메타데이터 추출 (duration, width, height)
            metadata = get_video_metadata(upload_data["object_key"])
            if metadata:
                if metadata.get("duration"):
                    vid_update["duration"] = metadata["duration"]
                if metadata.get("width"):
                    vid_update["width"] = metadata["width"]
                if metadata.get("height"):
                    vid_update["height"] = metadata["height"]

            # 비디오 썸네일 생성
            thumb_key = generate_video_thumbnail(
                org_id=str(org_id),
                object_key=upload_data["object_key"],
            )
            if thumb_key:
                vid_update["thumbnail_url"] = thumb_key

            if vid_update:
                asset = await self._repo.update_asset(asset.id, org_id, vid_update)
                logger.info(
                    "video_metadata_and_thumbnail_set",
                    asset_id=str(asset.id),
                    has_thumbnail=bool(thumb_key),
                    metadata_keys=list(vid_update.keys()),
                )

        # Real-time search indexing (best-effort)
        _index_media_to_search(asset)

        return asset

    async def update_asset(
        self, asset_id: UUID, org_id: UUID, data: dict
    ) -> MediaAsset:
        update_data: dict = {}
        if data.get("filename") is not None:
            update_data["filename"] = data["filename"]
        if data.get("tags") is not None:
            update_data["tags"] = data["tags"]
        if "folder_id" in data:
            folder_id = data["folder_id"]
            if folder_id is not None:
                update_data["folder_id"] = UUID(folder_id) if isinstance(folder_id, str) else folder_id
            else:
                update_data["folder_id"] = None

        if not update_data:
            return await self.get_asset(asset_id, org_id)

        asset = await self._repo.update_asset(asset_id, org_id, update_data)
        if asset is None:
            raise MediaNotFoundError()

        logger.info("media_asset_updated", asset_id=str(asset_id))
        _index_media_to_search(asset)
        return asset

    async def delete_asset(self, asset_id: UUID, org_id: UUID) -> None:
        deleted = await self._repo.soft_delete_asset(asset_id, org_id)
        if not deleted:
            raise MediaNotFoundError()
        logger.info("media_asset_deleted", asset_id=str(asset_id))
        _delete_media_from_search(asset_id)

    async def update_subtitles(
        self, asset_id: UUID, org_id: UUID, subtitles: list[dict], language: str
    ) -> MediaAsset:
        """Save subtitle data to the media asset's metadata JSONB field."""
        asset = await self.get_asset(asset_id, org_id)

        # Merge subtitles into existing metadata
        existing_metadata = asset.metadata_ or {}
        existing_metadata["subtitles"] = {
            "language": language,
            "segments": subtitles,
            "updated_at": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
        }

        updated = await self._repo.update_asset(
            asset_id, org_id, {"metadata_": existing_metadata}
        )
        if updated is None:
            raise MediaNotFoundError()

        logger.info(
            "media_subtitles_updated",
            asset_id=str(asset_id),
            language=language,
            segment_count=len(subtitles),
        )
        return updated

    async def list_folders(self, org_id: UUID) -> list[MediaFolder]:
        return await self._repo.list_folders(org_id)

    async def create_folder(
        self, org_id: UUID, name: str, parent_id: UUID | None
    ) -> MediaFolder:
        folder = await self._repo.create_folder(org_id, name, parent_id)
        logger.info("media_folder_created", folder_id=str(folder.id), name=name)
        return folder
