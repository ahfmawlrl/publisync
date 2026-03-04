"""Analytics repository — query layer for analytics data (Phase 1-B + Phase 3)."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import Channel
from app.models.comment import Comment
from app.models.content import PublishResult
from app.models.enums import PublishResultStatus


class AnalyticsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_performance_by_platform(
        self,
        org_id: UUID,
        platform: str | None = None,
    ) -> list:
        """Aggregate performance from publish_results grouped by platform."""
        stmt = (
            select(
                Channel.platform,
                func.sum(PublishResult.views).label("total_views"),
                func.sum(PublishResult.likes).label("total_likes"),
                func.sum(PublishResult.shares).label("total_shares"),
                func.sum(PublishResult.comments_count).label("total_comments"),
                func.count(PublishResult.id).label("result_count"),
            )
            .join(Channel, PublishResult.channel_id == Channel.id)
            .where(
                PublishResult.organization_id == org_id,
                PublishResult.status == PublishResultStatus.SUCCESS,
            )
        )

        if platform:
            stmt = stmt.where(Channel.platform == platform)

        stmt = stmt.group_by(Channel.platform)
        result = await self._db.execute(stmt)
        return result.all()

    async def get_engagement_heatmap(
        self,
        org_id: UUID,
    ) -> list:
        """Build engagement heatmap: hour × day_of_week from publish_results."""
        stmt = (
            select(
                extract("hour", PublishResult.created_at).label("hour"),
                extract("dow", PublishResult.created_at).label("day_of_week"),
                func.sum(
                    PublishResult.views
                    + PublishResult.likes
                    + PublishResult.shares
                    + PublishResult.comments_count
                ).label("value"),
            )
            .where(
                PublishResult.organization_id == org_id,
                PublishResult.status == PublishResultStatus.SUCCESS,
            )
            .group_by("hour", "day_of_week")
            .order_by("day_of_week", "hour")
        )
        result = await self._db.execute(stmt)
        return result.all()

    # ── Phase 3 — Sentiment Trend (F18) ──────────────────

    async def get_sentiment_trend(
        self,
        org_id: UUID,
        days: int = 30,
    ) -> list:
        """Daily sentiment distribution from comments."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = (
            select(
                func.date(Comment.created_at).label("date"),
                Comment.sentiment,
                func.count(Comment.id).label("count"),
            )
            .where(
                Comment.organization_id == org_id,
                Comment.created_at >= cutoff,
            )
            .group_by(func.date(Comment.created_at), Comment.sentiment)
            .order_by(func.date(Comment.created_at))
        )
        result = await self._db.execute(stmt)
        return result.all()

    async def get_keyword_frequency(
        self,
        org_id: UUID,
        days: int = 30,
    ) -> list:
        """Recent comment bodies for keyword extraction."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = (
            select(Comment.body, Comment.sentiment)
            .where(
                Comment.organization_id == org_id,
                Comment.created_at >= cutoff,
                Comment.body.isnot(None),
            )
            .limit(500)
        )
        result = await self._db.execute(stmt)
        return result.all()

    # ── Phase 3 — Prediction (F20) ───────────────────────

    async def get_prediction_data(
        self,
        org_id: UUID,
        content_id: UUID | None = None,
    ) -> dict:
        """Gather historical performance data for prediction."""
        cutoff_6m = datetime.now(timezone.utc) - timedelta(days=180)

        count_stmt = (
            select(func.count(PublishResult.id))
            .where(
                PublishResult.organization_id == org_id,
                PublishResult.status == PublishResultStatus.SUCCESS,
                PublishResult.created_at >= cutoff_6m,
            )
        )
        total_count = (await self._db.execute(count_stmt)).scalar() or 0

        # Average performance by platform
        avg_stmt = (
            select(
                Channel.platform,
                func.avg(PublishResult.views).label("avg_views"),
                func.avg(PublishResult.likes).label("avg_likes"),
                func.avg(PublishResult.shares).label("avg_shares"),
                func.count(PublishResult.id).label("sample_count"),
            )
            .join(Channel, PublishResult.channel_id == Channel.id)
            .where(
                PublishResult.organization_id == org_id,
                PublishResult.status == PublishResultStatus.SUCCESS,
                PublishResult.created_at >= cutoff_6m,
            )
            .group_by(Channel.platform)
        )
        result = await self._db.execute(avg_stmt)
        platform_avgs = [
            {
                "platform": r.platform.value if hasattr(r.platform, "value") else str(r.platform),
                "avg_views": float(r.avg_views or 0),
                "avg_likes": float(r.avg_likes or 0),
                "avg_shares": float(r.avg_shares or 0),
                "sample_count": r.sample_count,
            }
            for r in result.all()
        ]

        # Best performing hours
        engagement_expr = (
            PublishResult.views + PublishResult.likes
            + PublishResult.shares + PublishResult.comments_count
        )
        hour_stmt = (
            select(
                extract("dow", PublishResult.created_at).label("dow"),
                extract("hour", PublishResult.created_at).label("hour"),
                func.avg(engagement_expr).label("avg_engagement"),
            )
            .where(
                PublishResult.organization_id == org_id,
                PublishResult.status == PublishResultStatus.SUCCESS,
                PublishResult.created_at >= cutoff_6m,
            )
            .group_by("dow", "hour")
            .order_by(func.avg(engagement_expr).desc())
            .limit(5)
        )
        hour_result = await self._db.execute(hour_stmt)
        best_times = [
            {"dow": int(r.dow), "hour": int(r.hour), "avg_engagement": float(r.avg_engagement or 0)}
            for r in hour_result.all()
        ]

        return {
            "total_posts": total_count,
            "data_months": min(6, max(1, total_count // 30)) if total_count > 0 else 0,
            "platform_averages": platform_avgs,
            "best_times": best_times,
        }

    # ── Phase 4 — Benchmark (F23) ───────────────────────

    async def get_benchmark_data(
        self,
        org_id: UUID,
        period_days: int = 30,
    ) -> dict:
        """Get benchmark data comparing org performance vs all orgs."""
        from app.models.user import Organization

        cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)

        # Org's own performance
        org_stmt = (
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
                PublishResult.created_at >= cutoff,
            )
            .group_by(Channel.platform)
        )
        org_result = await self._db.execute(org_stmt)
        org_data = org_result.all()

        # All orgs performance (for industry average)
        all_stmt = (
            select(
                Channel.platform,
                PublishResult.organization_id,
                func.sum(PublishResult.views).label("total_views"),
                func.sum(PublishResult.likes).label("total_likes"),
                func.sum(PublishResult.shares).label("total_shares"),
                func.sum(PublishResult.comments_count).label("total_comments"),
                func.count(PublishResult.id).label("post_count"),
            )
            .join(Channel, PublishResult.channel_id == Channel.id)
            .where(
                PublishResult.status == PublishResultStatus.SUCCESS,
                PublishResult.created_at >= cutoff,
            )
            .group_by(Channel.platform, PublishResult.organization_id)
        )
        all_result = await self._db.execute(all_stmt)
        all_data = all_result.all()

        return {"org_data": org_data, "all_data": all_data}

    async def get_org_comparison_data(
        self,
        org_ids: list[UUID],
        period_days: int = 30,
    ) -> list:
        """Get comparison data across multiple organizations."""
        from app.models.user import Organization

        cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)

        stmt = (
            select(
                PublishResult.organization_id,
                Organization.name.label("org_name"),
                Channel.platform,
                func.sum(PublishResult.views).label("total_views"),
                func.sum(PublishResult.likes).label("total_likes"),
                func.sum(PublishResult.shares).label("total_shares"),
                func.sum(PublishResult.comments_count).label("total_comments"),
                func.count(PublishResult.id).label("post_count"),
            )
            .join(Channel, PublishResult.channel_id == Channel.id)
            .join(Organization, PublishResult.organization_id == Organization.id)
            .where(
                PublishResult.organization_id.in_(org_ids),
                PublishResult.status == PublishResultStatus.SUCCESS,
                PublishResult.created_at >= cutoff,
            )
            .group_by(
                PublishResult.organization_id,
                Organization.name,
                Channel.platform,
            )
            .order_by(Organization.name, Channel.platform)
        )
        result = await self._db.execute(stmt)
        return result.all()
