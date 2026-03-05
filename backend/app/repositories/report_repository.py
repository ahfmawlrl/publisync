"""Report repository — query layer for reports (Phase 3)."""

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import Channel
from app.models.comment import Comment
from app.models.content import Content, PublishResult
from app.models.enums import PublishResultStatus
from app.models.report import Report


class ReportRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    @property
    def db(self) -> AsyncSession:
        return self._db

    async def list_reports(
        self,
        org_id: UUID,
        period: str | None = None,
        status: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Report], int]:
        stmt = select(Report).where(Report.organization_id == org_id)
        count_stmt = select(func.count(Report.id)).where(Report.organization_id == org_id)

        if period:
            stmt = stmt.where(Report.period == period)
            count_stmt = count_stmt.where(Report.period == period)
        if status:
            stmt = stmt.where(Report.status == status)
            count_stmt = count_stmt.where(Report.status == status)

        total = (await self._db.execute(count_stmt)).scalar() or 0
        stmt = stmt.order_by(Report.created_at.desc()).offset((page - 1) * limit).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_id(self, report_id: UUID, org_id: UUID) -> Report | None:
        stmt = select(Report).where(Report.id == report_id, Report.organization_id == org_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, report: Report) -> Report:
        self._db.add(report)
        await self._db.flush()
        await self._db.refresh(report)
        return report

    async def update(self, report: Report) -> Report:
        await self._db.flush()
        await self._db.refresh(report)
        return report

    async def get_analytics_data(
        self, org_id: UUID, start: date, end: date
    ) -> dict:
        """Aggregate performance data for report generation."""
        stmt = (
            select(
                Channel.platform,
                func.sum(PublishResult.views).label("total_views"),
                func.sum(PublishResult.likes).label("total_likes"),
                func.sum(PublishResult.shares).label("total_shares"),
                func.sum(PublishResult.comments_count).label("total_comments"),
                func.count(PublishResult.id).label("post_count"),
            )
            .join(Channel, PublishResult.channel_id == Channel.id)
            .where(
                PublishResult.organization_id == org_id,
                PublishResult.status == PublishResultStatus.SUCCESS,
                func.date(PublishResult.created_at) >= start,
                func.date(PublishResult.created_at) <= end,
            )
            .group_by(Channel.platform)
        )
        result = await self._db.execute(stmt)
        rows = result.all()
        return {
            "platforms": [
                {
                    "platform": str(r.platform.value) if hasattr(r.platform, "value") else str(r.platform),
                    "total_views": r.total_views or 0,
                    "total_likes": r.total_likes or 0,
                    "total_shares": r.total_shares or 0,
                    "total_comments": r.total_comments or 0,
                    "post_count": r.post_count or 0,
                }
                for r in rows
            ]
        }

    async def get_sentiment_summary(
        self, org_id: UUID, start: date, end: date
    ) -> dict:
        """Aggregate comment sentiment distribution."""
        stmt = (
            select(
                Comment.sentiment,
                func.count(Comment.id).label("count"),
            )
            .where(
                Comment.organization_id == org_id,
                func.date(Comment.created_at) >= start,
                func.date(Comment.created_at) <= end,
            )
            .group_by(Comment.sentiment)
        )
        result = await self._db.execute(stmt)
        rows = result.all()
        return {
            str(r.sentiment.value) if hasattr(r.sentiment, "value") else str(r.sentiment): r.count
            for r in rows
        }

    async def get_top_contents(
        self, org_id: UUID, start: date, end: date, limit: int = 5
    ) -> list[dict]:
        """Get top performing contents by total engagement."""
        engagement_expr = (
            PublishResult.views + PublishResult.likes
            + PublishResult.shares + PublishResult.comments_count
        )
        stmt = (
            select(
                Content.id,
                Content.title,
                func.sum(engagement_expr).label("engagement"),
            )
            .join(PublishResult, PublishResult.content_id == Content.id)
            .where(
                Content.organization_id == org_id,
                PublishResult.status == PublishResultStatus.SUCCESS,
                func.date(PublishResult.created_at) >= start,
                func.date(PublishResult.created_at) <= end,
            )
            .group_by(Content.id, Content.title)
            .order_by(func.sum(engagement_expr).desc())
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        return [
            {"id": str(r.id), "title": r.title, "engagement": r.engagement or 0}
            for r in result.all()
        ]
