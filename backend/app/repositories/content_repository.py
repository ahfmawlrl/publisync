"""Repository for Content, ContentVersion, PublishResult — S5 (F01)."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.content import Content, ContentVersion, PublishResult
from app.models.enums import ContentStatus, PublishResultStatus


class ContentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Content ──────────────────────────────────────────

    async def get_by_id(self, content_id: UUID) -> Content | None:
        stmt = (
            select(Content)
            .where(Content.id == content_id, Content.deleted_at.is_(None))
            .options(selectinload(Content.publish_results))
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_contents(
        self,
        org_id: UUID,
        offset: int = 0,
        limit: int = 20,
        status: str | None = None,
        platform: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Content], int]:
        base = select(Content).where(
            Content.organization_id == org_id,
            Content.deleted_at.is_(None),
        )
        count_base = select(func.count()).select_from(Content).where(
            Content.organization_id == org_id,
            Content.deleted_at.is_(None),
        )

        if status:
            base = base.where(Content.status == status)
            count_base = count_base.where(Content.status == status)
        if platform:
            base = base.where(Content.platforms.any(platform))
            count_base = count_base.where(Content.platforms.any(platform))
        if search:
            base = base.where(Content.title.ilike(f"%{search}%"))
            count_base = count_base.where(Content.title.ilike(f"%{search}%"))

        total = (await self._db.execute(count_base)).scalar() or 0
        stmt = base.order_by(Content.created_at.desc()).offset(offset).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all()), total

    async def create(self, content: Content) -> Content:
        self._db.add(content)
        await self._db.flush()
        return content

    async def update(self, content: Content, data: dict) -> Content:
        for key, value in data.items():
            setattr(content, key, value)
        await self._db.flush()
        return content

    async def soft_delete(self, content: Content) -> None:
        from datetime import datetime, timezone

        content.deleted_at = datetime.now(timezone.utc)
        await self._db.flush()

    async def get_scheduled_contents(self, before_dt: str) -> list[Content]:
        """Get contents scheduled for publishing before the given datetime."""
        stmt = select(Content).where(
            Content.status == ContentStatus.SCHEDULED,
            Content.scheduled_at.isnot(None),
            Content.scheduled_at <= before_dt,
            Content.deleted_at.is_(None),
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    # ── ContentVersion ───────────────────────────────────

    async def add_version(self, version: ContentVersion) -> ContentVersion:
        self._db.add(version)
        await self._db.flush()
        return version

    async def get_latest_version_number(self, content_id: UUID) -> int:
        stmt = (
            select(func.coalesce(func.max(ContentVersion.version), 0))
            .where(ContentVersion.content_id == content_id)
        )
        result = await self._db.execute(stmt)
        return result.scalar() or 0

    # ── PublishResult ────────────────────────────────────

    async def add_publish_result(self, pr: PublishResult) -> PublishResult:
        self._db.add(pr)
        await self._db.flush()
        return pr

    async def list_publish_results(
        self, content_id: UUID, offset: int = 0, limit: int = 50
    ) -> tuple[list[PublishResult], int]:
        base = select(PublishResult).where(PublishResult.content_id == content_id)
        count_q = select(func.count()).select_from(PublishResult).where(PublishResult.content_id == content_id)

        total = (await self._db.execute(count_q)).scalar() or 0
        stmt = base.order_by(PublishResult.created_at.desc()).offset(offset).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_publish_result(self, result_id: UUID) -> PublishResult | None:
        return await self._db.get(PublishResult, result_id)

    async def count_results_by_status(self, content_id: UUID) -> dict[str, int]:
        """Count publish results per status for PARTIALLY_PUBLISHED judgment."""
        stmt = (
            select(PublishResult.status, func.count())
            .where(PublishResult.content_id == content_id)
            .group_by(PublishResult.status)
        )
        result = await self._db.execute(stmt)
        return {row[0].value if hasattr(row[0], "value") else row[0]: row[1] for row in result.all()}
