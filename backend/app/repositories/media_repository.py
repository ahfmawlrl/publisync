"""Repository for MediaAsset, MediaFolder — Phase 2 (F11)."""

from datetime import UTC, datetime, timedelta
from typing import ClassVar
from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Content
from app.models.media import MediaAsset, MediaFolder


def _escape_like(value: str) -> str:
    """Escape LIKE/ILIKE wildcard characters to prevent unintended pattern matching."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class MediaRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── MediaAsset ────────────────────────────────────────

    # 허용된 정렬 옵션 매핑
    _SORT_MAP: ClassVar[dict[str, tuple]] = {
        "newest": (MediaAsset.created_at.desc,),
        "oldest": (MediaAsset.created_at.asc,),
        "name_asc": (MediaAsset.filename.asc,),
        "name_desc": (MediaAsset.filename.desc,),
        "size_desc": (MediaAsset.file_size.desc,),
        "size_asc": (MediaAsset.file_size.asc,),
    }

    async def list_assets(
        self,
        org_id: UUID,
        offset: int = 0,
        limit: int = 20,
        media_type: str | None = None,
        folder_id: UUID | None = None,
        search: str | None = None,
        tags: list[str] | None = None,
        sort: str = "newest",
    ) -> tuple[list[MediaAsset], int]:
        base = select(MediaAsset).where(
            MediaAsset.organization_id == org_id,
            MediaAsset.deleted_at.is_(None),
        )
        count_base = select(func.count()).select_from(MediaAsset).where(
            MediaAsset.organization_id == org_id,
            MediaAsset.deleted_at.is_(None),
        )

        if media_type:
            base = base.where(MediaAsset.media_type == media_type)
            count_base = count_base.where(MediaAsset.media_type == media_type)
        if folder_id is not None:
            base = base.where(MediaAsset.folder_id == folder_id)
            count_base = count_base.where(MediaAsset.folder_id == folder_id)
        if search:
            escaped = _escape_like(search)
            base = base.where(MediaAsset.filename.ilike(f"%{escaped}%"))
            count_base = count_base.where(MediaAsset.filename.ilike(f"%{escaped}%"))
        if tags:
            base = base.where(MediaAsset.tags.overlap(tags))
            count_base = count_base.where(MediaAsset.tags.overlap(tags))

        total = (await self._db.execute(count_base)).scalar() or 0

        # 정렬 적용
        sort_fns = self._SORT_MAP.get(sort, self._SORT_MAP["newest"])
        for fn in sort_fns:
            base = base.order_by(fn())

        stmt = base.offset(offset).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_asset(self, asset_id: UUID, org_id: UUID) -> MediaAsset | None:
        stmt = select(MediaAsset).where(
            MediaAsset.id == asset_id,
            MediaAsset.organization_id == org_id,
            MediaAsset.deleted_at.is_(None),
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_asset(self, data: dict) -> MediaAsset:
        asset = MediaAsset(**data)
        self._db.add(asset)
        await self._db.flush()
        await self._db.refresh(asset)
        return asset

    async def update_asset(self, asset_id: UUID, org_id: UUID, data: dict) -> MediaAsset | None:
        asset = await self.get_asset(asset_id, org_id)
        if asset is None:
            return None
        for key, value in data.items():
            setattr(asset, key, value)
        await self._db.flush()
        await self._db.refresh(asset)
        return asset

    async def soft_delete_asset(self, asset_id: UUID, org_id: UUID) -> bool:
        asset = await self.get_asset(asset_id, org_id)
        if asset is None:
            return False
        asset.deleted_at = datetime.now(UTC)
        await self._db.flush()
        return True

    # ── Content Usage Count ─────────────────────────────────

    async def get_content_usage_counts(
        self, org_id: UUID, object_keys: list[str],
    ) -> dict[str, int]:
        """주어진 object_key 목록에 대해 해당 파일을 참조하는 콘텐츠 수를 반환.

        Contents.media_urls (ARRAY[String])에 object_key가 포함된 콘텐츠를 카운트합니다.
        """
        if not object_keys:
            return {}

        # PostgreSQL: media_urls @> ARRAY[key]::varchar[]  per key
        # 효율적인 batch 처리를 위해 unnest + group by 사용
        stmt = (
            select(
                func.unnest(Content.media_urls).label("url"),
                func.count().label("cnt"),
            )
            .where(
                Content.organization_id == org_id,
                Content.media_urls.isnot(None),
            )
            .group_by("url")
        )
        result = await self._db.execute(stmt)
        rows = result.all()

        # object_key → count 매핑
        url_counts: dict[str, int] = {row.url: row.cnt for row in rows}

        return {key: url_counts.get(key, 0) for key in object_keys}

    # ── Storage Quota ─────────────────────────────────────

    async def get_org_storage_usage(self, org_id: UUID) -> int:
        """기관별 전체 스토리지 사용량 반환 (bytes). soft-delete 제외."""
        stmt = (
            select(func.coalesce(func.sum(MediaAsset.file_size), 0))
            .where(
                MediaAsset.organization_id == org_id,
                MediaAsset.deleted_at.is_(None),
            )
        )
        result = await self._db.execute(stmt)
        return result.scalar() or 0

    # ── Soft-Delete Cleanup ───────────────────────────────

    async def get_expired_deleted_assets(self, days: int = 30) -> list[MediaAsset]:
        """삭제 후 일정 기간이 지난 에셋 목록 조회 (영구 삭제 대상).

        Args:
            days: soft-delete 후 보관 기간 (기본 30일).

        Returns:
            영구 삭제 대상 MediaAsset 목록.
        """
        cutoff = datetime.now(UTC) - timedelta(days=days)
        stmt = select(MediaAsset).where(
            MediaAsset.deleted_at.is_not(None),
            MediaAsset.deleted_at < cutoff,
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def hard_delete_asset(self, asset_id: UUID) -> None:
        """에셋을 데이터베이스에서 영구 삭제."""
        stmt = sa_delete(MediaAsset).where(MediaAsset.id == asset_id)
        await self._db.execute(stmt)
        await self._db.flush()

    # ── MediaFolder ───────────────────────────────────────

    async def list_folders(self, org_id: UUID) -> list[MediaFolder]:
        stmt = (
            select(MediaFolder)
            .where(MediaFolder.organization_id == org_id)
            .order_by(MediaFolder.name)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_folder_by_name(
        self, org_id: UUID, name: str, parent_id: UUID | None
    ) -> MediaFolder | None:
        """Check if a folder with the same name exists under the same parent."""
        stmt = select(MediaFolder).where(
            MediaFolder.organization_id == org_id,
            MediaFolder.name == name,
        )
        if parent_id is not None:
            stmt = stmt.where(MediaFolder.parent_id == parent_id)
        else:
            stmt = stmt.where(MediaFolder.parent_id.is_(None))
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_folder(self, org_id: UUID, name: str, parent_id: UUID | None) -> MediaFolder:
        folder = MediaFolder(
            organization_id=org_id,
            name=name,
            parent_id=parent_id,
        )
        self._db.add(folder)
        await self._db.flush()
        await self._db.refresh(folder)
        return folder
