"""Analytics repository — query layer for analytics data (Phase 1-B + Phase 3)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import extract, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import Channel
from app.models.comment import Comment
from app.models.content import Content, PublishResult
from app.models.enums import PublishResultStatus


class AnalyticsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_performance_by_platform(
        self,
        org_id: UUID,
        platform: str | None = None,
        days: int = 30,
    ) -> list:
        """Aggregate performance from publish_results grouped by platform."""
        cutoff = datetime.now(UTC) - timedelta(days=days)
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
                PublishResult.created_at >= cutoff,
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
        days: int = 30,
    ) -> list:
        """Build engagement heatmap: hour × day_of_week from publish_results.

        Returns day_of_week as ISO convention: 0=Monday .. 6=Sunday
        (converted from PostgreSQL DOW where 0=Sunday).
        """
        cutoff = datetime.now(UTC) - timedelta(days=days)
        # PostgreSQL ISODOW: 1=Monday..7=Sunday → subtract 1 → 0=Monday..6=Sunday
        iso_dow_expr = (extract("isodow", PublishResult.created_at) - 1).label("day_of_week")
        stmt = (
            select(
                extract("hour", PublishResult.created_at).label("hour"),
                iso_dow_expr,
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
                PublishResult.created_at >= cutoff,
            )
            .group_by("hour", iso_dow_expr)
            .order_by(iso_dow_expr, "hour")
        )
        result = await self._db.execute(stmt)
        return result.all()

    # ── Trend & Top Contents (S12 — F06) ────────────────

    async def get_trend_data(
        self,
        org_id: UUID,
        days: int = 30,
        granularity: str = "daily",
    ) -> list:
        """Time-series reach (views) + engagement grouped by date bucket."""
        cutoff = datetime.now(UTC) - timedelta(days=days)

        if granularity == "weekly":
            date_expr = func.date_trunc("week", PublishResult.created_at)
        elif granularity == "monthly":
            date_expr = func.date_trunc("month", PublishResult.created_at)
        else:
            date_expr = func.date(PublishResult.created_at)

        engagement_expr = (
            PublishResult.likes + PublishResult.shares + PublishResult.comments_count
        )
        stmt = (
            select(
                date_expr.label("date_bucket"),
                func.coalesce(func.sum(PublishResult.views), 0).label("reach"),
                func.coalesce(func.sum(engagement_expr), 0).label("engagement"),
            )
            .where(
                PublishResult.organization_id == org_id,
                PublishResult.status == PublishResultStatus.SUCCESS,
                PublishResult.created_at >= cutoff,
            )
            .group_by(date_expr)
            .order_by(date_expr)
        )
        result = await self._db.execute(stmt)
        return result.all()

    async def get_top_contents_data(
        self,
        org_id: UUID,
        days: int = 30,
        limit: int = 5,
    ) -> list:
        """Top N contents by total views within period."""
        cutoff = datetime.now(UTC) - timedelta(days=days)

        stmt = (
            select(
                Content.id.label("content_id"),
                Content.title,
                Channel.platform,
                func.coalesce(func.sum(PublishResult.views), 0).label("total_views"),
            )
            .join(PublishResult, PublishResult.content_id == Content.id)
            .join(Channel, PublishResult.channel_id == Channel.id)
            .where(
                Content.organization_id == org_id,
                PublishResult.status == PublishResultStatus.SUCCESS,
                PublishResult.created_at >= cutoff,
            )
            .group_by(Content.id, Content.title, Channel.platform)
            .order_by(func.sum(PublishResult.views).desc())
            .limit(limit)
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
        cutoff = datetime.now(UTC) - timedelta(days=days)
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
        cutoff = datetime.now(UTC) - timedelta(days=days)
        stmt = (
            select(Comment.text, Comment.sentiment)
            .where(
                Comment.organization_id == org_id,
                Comment.created_at >= cutoff,
                Comment.text.isnot(None),
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
        cutoff_6m = datetime.now(UTC) - timedelta(days=180)

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

    async def _temporarily_bypass_rls(self) -> str:
        """Temporarily elevate to SA role for cross-org queries, return original role."""
        result = await self._db.execute(text("SELECT current_setting('app.user_role', true)"))
        original_role = result.scalar() or "AGENCY_MANAGER"
        await self._db.execute(text("SET LOCAL app.user_role = 'SYSTEM_ADMIN'"))
        return original_role

    async def _restore_rls(self, original_role: str) -> None:
        """Restore original user role after cross-org query."""
        await self._db.execute(text(f"SET LOCAL app.user_role = '{original_role}'"))

    async def get_benchmark_data(
        self,
        org_id: UUID,
        period_days: int = 30,
    ) -> dict:
        """Get benchmark data comparing org performance vs all orgs."""

        cutoff = datetime.now(UTC) - timedelta(days=period_days)

        # Org's own performance (uses normal RLS — current org only)
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
        # Temporarily bypass RLS to read cross-org aggregate data
        original_role = await self._temporarily_bypass_rls()
        try:
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
        finally:
            await self._restore_rls(original_role)

        return {"org_data": org_data, "all_data": all_data}

    async def get_org_comparison_data(
        self,
        org_ids: list[UUID],
        period_days: int = 30,
    ) -> list:
        """Get comparison data across multiple organizations."""
        from app.models.user import Organization

        cutoff = datetime.now(UTC) - timedelta(days=period_days)

        # Temporarily bypass RLS to read cross-org comparison data
        original_role = await self._temporarily_bypass_rls()
        try:
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
        finally:
            await self._restore_rls(original_role)
