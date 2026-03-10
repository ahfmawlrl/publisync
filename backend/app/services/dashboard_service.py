"""Dashboard business logic — S7."""

from datetime import UTC, datetime, time, timedelta
from uuid import UUID

import structlog
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import ApprovalRequest
from app.models.channel import Channel
from app.models.comment import Comment
from app.models.content import Content, PublishResult
from app.models.enums import (
    ApprovalStatus,
    ChannelStatus,
    ContentStatus,
    OrgStatus,
    PublishResultStatus,
)
from app.models.user import Organization
from app.schemas.dashboard import (
    ApprovalStatusItem,
    DashboardSummaryResponse,
    OrgSummaryItem,
    PlatformTrendItem,
    RecentContentItem,
    SentimentSummaryItem,
    TodayScheduleItem,
)

logger = structlog.get_logger()


def _period_start(period: str) -> datetime | None:
    """Convert period string ('7d', '30d') to a start datetime."""
    days = {"7d": 7, "30d": 30}.get(period)
    if days is None:
        return None
    return datetime.now(UTC) - timedelta(days=days)


class DashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_summary(self, org_id: UUID, period: str = "7d") -> DashboardSummaryResponse:
        """Dashboard KPI summary with basic counts."""
        period_start = _period_start(period)

        # Total contents (within period if applicable)
        total_q = select(func.count()).select_from(Content).where(
            Content.organization_id == org_id, Content.deleted_at.is_(None)
        )
        if period_start:
            total_q = total_q.where(Content.created_at >= period_start)
        total = (await self._db.execute(total_q)).scalar() or 0

        # Published
        pub_q = select(func.count()).select_from(Content).where(
            Content.organization_id == org_id,
            Content.status == ContentStatus.PUBLISHED,
            Content.deleted_at.is_(None),
        )
        if period_start:
            pub_q = pub_q.where(Content.created_at >= period_start)
        published = (await self._db.execute(pub_q)).scalar() or 0

        # Scheduled
        sched_q = select(func.count()).select_from(Content).where(
            Content.organization_id == org_id,
            Content.status == ContentStatus.SCHEDULED,
            Content.deleted_at.is_(None),
        )
        scheduled = (await self._db.execute(sched_q)).scalar() or 0

        # Pending approvals
        pend_q = select(func.count()).select_from(ApprovalRequest).where(
            ApprovalRequest.organization_id == org_id,
            ApprovalRequest.status.in_([ApprovalStatus.PENDING_REVIEW, ApprovalStatus.IN_REVIEW]),
        )
        pending = (await self._db.execute(pend_q)).scalar() or 0

        # Active channels
        chan_q = select(func.count()).select_from(Channel).where(
            Channel.organization_id == org_id,
            Channel.status == ChannelStatus.ACTIVE,
        )
        active_channels = (await self._db.execute(chan_q)).scalar() or 0

        # Total views/likes from publish results
        stats_q = select(
            func.coalesce(func.sum(PublishResult.views), 0),
            func.coalesce(func.sum(PublishResult.likes), 0),
        ).where(PublishResult.organization_id == org_id)
        if period_start:
            stats_q = stats_q.where(PublishResult.created_at >= period_start)
        stats = (await self._db.execute(stats_q)).one()

        return DashboardSummaryResponse(
            total_contents=total,
            published_contents=published,
            scheduled_contents=scheduled,
            pending_approvals=pending,
            active_channels=active_channels,
            total_views=stats[0],
            total_likes=stats[1],
        )

    async def get_platform_trends(self, org_id: UUID, period: str = "7d") -> list[PlatformTrendItem]:
        """Aggregate publish results by platform."""
        stmt = (
            select(
                Channel.platform,
                func.count(PublishResult.id),
                func.coalesce(func.sum(PublishResult.views), 0),
                func.coalesce(func.sum(PublishResult.likes), 0),
                func.coalesce(func.sum(PublishResult.shares), 0),
            )
            .join(Channel, PublishResult.channel_id == Channel.id)
            .where(
                PublishResult.organization_id == org_id,
                PublishResult.status == PublishResultStatus.SUCCESS,
            )
            .group_by(Channel.platform)
        )
        period_start = _period_start(period)
        if period_start:
            stmt = stmt.where(PublishResult.created_at >= period_start)

        result = await self._db.execute(stmt)
        return [
            PlatformTrendItem(
                platform=row[0].value if hasattr(row[0], "value") else row[0],
                published=row[1],
                views=row[2],
                likes=row[3],
                shares=row[4],
            )
            for row in result.all()
        ]

    async def get_approval_status(self, org_id: UUID) -> list[ApprovalStatusItem]:
        """Count approval requests by status."""
        stmt = (
            select(ApprovalRequest.status, func.count())
            .where(ApprovalRequest.organization_id == org_id)
            .group_by(ApprovalRequest.status)
        )
        result = await self._db.execute(stmt)
        return [
            ApprovalStatusItem(
                status=row[0].value if hasattr(row[0], "value") else row[0],
                count=row[1],
            )
            for row in result.all()
        ]

    async def get_recent_contents(self, org_id: UUID, limit: int = 10) -> list[RecentContentItem]:
        """Get most recently created contents."""
        stmt = (
            select(Content)
            .where(Content.organization_id == org_id, Content.deleted_at.is_(None))
            .order_by(Content.created_at.desc())
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        return [
            RecentContentItem(
                id=str(c.id),
                title=c.title,
                status=c.status.value,
                platforms=c.platforms or [],
                created_at=c.created_at.isoformat(),
                author_id=str(c.author_id),
            )
            for c in result.scalars().all()
        ]

    async def get_today_schedule(self, org_id: UUID) -> list[TodayScheduleItem]:
        """Get contents scheduled for today."""
        now = datetime.now(UTC)
        today_start = datetime.combine(now.date(), time.min, tzinfo=UTC)
        today_end = datetime.combine(now.date(), time.max, tzinfo=UTC)

        stmt = (
            select(Content)
            .where(
                Content.organization_id == org_id,
                Content.status == ContentStatus.SCHEDULED,
                Content.scheduled_at >= today_start,
                Content.scheduled_at <= today_end,
                Content.deleted_at.is_(None),
            )
            .order_by(Content.scheduled_at)
        )
        result = await self._db.execute(stmt)
        return [
            TodayScheduleItem(
                id=str(c.id),
                title=c.title,
                scheduled_at=c.scheduled_at.isoformat() if c.scheduled_at else "",
                platforms=c.platforms or [],
                status=c.status.value,
            )
            for c in result.scalars().all()
        ]

    async def get_sentiment_summary(self, org_id: UUID, period: str = "7d") -> list[SentimentSummaryItem]:
        """Count comments by sentiment for donut chart."""
        stmt = (
            select(Comment.sentiment, func.count())
            .where(
                Comment.organization_id == org_id,
                Comment.sentiment.isnot(None),
            )
            .group_by(Comment.sentiment)
        )
        period_start = _period_start(period)
        if period_start:
            stmt = stmt.where(Comment.created_at >= period_start)

        result = await self._db.execute(stmt)
        rows = result.all()
        total = sum(r[1] for r in rows) or 1  # avoid division by zero

        return [
            SentimentSummaryItem(
                sentiment=row[0].value if hasattr(row[0], "value") else row[0],
                count=row[1],
                percentage=round(row[1] / total * 100, 1),
            )
            for row in rows
        ]

    async def get_all_organizations_summary(self) -> list[OrgSummaryItem]:
        """AM-only: get summary for all organizations using aggregated queries."""
        # Set RLS bypass — this endpoint is restricted to AM/SA via require_roles.
        # Both variables must be set: tenant_isolation policy calls
        # current_setting('app.current_org_id') without missing_ok, which would
        # throw if unset. A nil UUID ensures no error while sa_bypass grants access.
        await self._db.execute(text("SET LOCAL app.current_org_id = '00000000-0000-0000-0000-000000000000'"))
        await self._db.execute(text("SET LOCAL app.user_role = 'SYSTEM_ADMIN'"))

        # Fetch all active orgs
        org_stmt = select(Organization.id, Organization.name, Organization.slug).where(
            Organization.status == OrgStatus.ACTIVE,
        )
        org_result = await self._db.execute(org_stmt)
        orgs = org_result.all()

        if not orgs:
            return []

        org_ids = [o.id for o in orgs]

        # Aggregate content counts in one query
        content_stmt = (
            select(
                Content.organization_id,
                func.count().label("total"),
                func.count().filter(Content.status == ContentStatus.PUBLISHED).label("published"),
            )
            .where(Content.organization_id.in_(org_ids), Content.deleted_at.is_(None))
            .group_by(Content.organization_id)
        )
        content_result = await self._db.execute(content_stmt)
        content_map: dict[UUID, tuple[int, int]] = {}
        for row in content_result.all():
            content_map[row[0]] = (row[1], row[2])

        # Aggregate channel counts in one query
        channel_stmt = (
            select(Channel.organization_id, func.count())
            .where(Channel.organization_id.in_(org_ids), Channel.status == ChannelStatus.ACTIVE)
            .group_by(Channel.organization_id)
        )
        channel_result = await self._db.execute(channel_stmt)
        channel_map: dict[UUID, int] = {row[0]: row[1] for row in channel_result.all()}

        # Aggregate pending approval counts in one query
        approval_stmt = (
            select(ApprovalRequest.organization_id, func.count())
            .where(
                ApprovalRequest.organization_id.in_(org_ids),
                ApprovalRequest.status.in_([ApprovalStatus.PENDING_REVIEW, ApprovalStatus.IN_REVIEW]),
            )
            .group_by(ApprovalRequest.organization_id)
        )
        approval_result = await self._db.execute(approval_stmt)
        approval_map: dict[UUID, int] = {row[0]: row[1] for row in approval_result.all()}

        return [
            OrgSummaryItem(
                id=str(org.id),
                name=org.name,
                slug=org.slug,
                total_contents=content_map.get(org.id, (0, 0))[0],
                published_contents=content_map.get(org.id, (0, 0))[1],
                active_channels=channel_map.get(org.id, 0),
                pending_approvals=approval_map.get(org.id, 0),
            )
            for org in orgs
        ]
