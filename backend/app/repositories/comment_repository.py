"""Repository for Comment and ReplyTemplate — S9 (F04)."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment, ReplyTemplate
from app.models.enums import CommentSentiment


class CommentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Comment queries ──────────────────────────────────

    async def list_comments(
        self,
        org_id: UUID,
        offset: int = 0,
        limit: int = 20,
        status: str | None = None,
        platform: str | None = None,
        channel_id: UUID | None = None,
        search: str | None = None,
    ) -> tuple[list[Comment], int]:
        base = select(Comment).where(Comment.organization_id == org_id)
        count_base = select(func.count()).select_from(Comment).where(
            Comment.organization_id == org_id
        )

        if status:
            base = base.where(Comment.status == status)
            count_base = count_base.where(Comment.status == status)
        if platform:
            base = base.where(Comment.platform == platform)
            count_base = count_base.where(Comment.platform == platform)
        if channel_id:
            base = base.where(Comment.channel_id == channel_id)
            count_base = count_base.where(Comment.channel_id == channel_id)
        if search:
            like_pattern = f"%{search}%"
            base = base.where(
                Comment.text.ilike(like_pattern) | Comment.author_name.ilike(like_pattern)
            )
            count_base = count_base.where(
                Comment.text.ilike(like_pattern) | Comment.author_name.ilike(like_pattern)
            )

        total = (await self._db.execute(count_base)).scalar() or 0
        stmt = base.order_by(Comment.created_at.desc()).offset(offset).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_comment(self, comment_id: UUID) -> Comment | None:
        stmt = select(Comment).where(Comment.id == comment_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_dangerous_comments(
        self,
        org_id: UUID,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Comment], int]:
        base = select(Comment).where(
            Comment.organization_id == org_id,
            Comment.sentiment == CommentSentiment.DANGEROUS,
        )
        count_base = select(func.count()).select_from(Comment).where(
            Comment.organization_id == org_id,
            Comment.sentiment == CommentSentiment.DANGEROUS,
        )

        total = (await self._db.execute(count_base)).scalar() or 0
        stmt = base.order_by(Comment.created_at.desc()).offset(offset).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all()), total

    async def update_comment(self, comment: Comment, data: dict) -> Comment:
        for key, value in data.items():
            setattr(comment, key, value)
        await self._db.flush()
        return comment

    # ── ReplyTemplate queries ────────────────────────────

    async def list_templates(
        self,
        org_id: UUID,
        category: str | None = None,
    ) -> list[ReplyTemplate]:
        base = select(ReplyTemplate).where(
            ReplyTemplate.organization_id == org_id,
            ReplyTemplate.deleted_at.is_(None),
        )
        if category:
            base = base.where(ReplyTemplate.category == category)

        stmt = base.order_by(ReplyTemplate.created_at.desc())
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_template(self, template_id: UUID) -> ReplyTemplate | None:
        stmt = select(ReplyTemplate).where(
            ReplyTemplate.id == template_id,
            ReplyTemplate.deleted_at.is_(None),
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_template(self, template: ReplyTemplate) -> ReplyTemplate:
        self._db.add(template)
        await self._db.flush()
        return template

    async def update_template(self, template: ReplyTemplate, data: dict) -> ReplyTemplate:
        for key, value in data.items():
            setattr(template, key, value)
        await self._db.flush()
        return template

    async def soft_delete_template(self, template: ReplyTemplate) -> None:
        template.deleted_at = datetime.now(UTC)
        await self._db.flush()
