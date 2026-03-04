"""Dashboard business logic — S7."""

import structlog
from datetime import datetime, time, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import ApprovalRequest
from app.models.channel import Channel
from app.models.content import Content, PublishResult
from app.models.enums import ApprovalStatus, ChannelStatus, ContentStatus, PublishResultStatus
from app.models.user import Organization
from app.models.comment import Comment
from app.models.enums import CommentSentiment
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


class DashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_summary(self, org_id: UUID) -> DashboardSummaryResponse:
        """Dashboard KPI summary with basic counts."""
        # Total contents
        total_q = select(func.count()).select_from(Content).where(
            Content.organization_id == org_id, Content.deleted_at.is_(None)
        )
        total = (await self._db.execute(total_q)).scalar() or 0

        # Published
        pub_q = select(func.count()).select_from(Content).where(
            Content.organization_id == org_id,
            Content.status == ContentStatus.PUBLISHED,
            Content.deleted_at.is_(None),
        )
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

    async def get_platform_trends(self, org_id: UUID) -> list[PlatformTrendItem]:
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
        now = datetime.now(timezone.utc)
        today_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
        today_end = datetime.combine(now.date(), time.max, tzinfo=timezone.utc)

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

    async def get_sentiment_summary(self, org_id: UUID) -> list[SentimentSummaryItem]:
        """Count comments by sentiment for donut chart."""
        stmt = (
            select(Comment.sentiment, func.count())
            .where(
                Comment.organization_id == org_id,
                Comment.sentiment.isnot(None),
            )
            .group_by(Comment.sentiment)
        )
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
        """AM-only: get summary for all organizations."""
        stmt = select(Organization).where(Organization.status == "ACTIVE")
        result = await self._db.execute(stmt)
        orgs = result.scalars().all()

        summaries = []
        for org in orgs:
            content_q = select(func.count()).select_from(Content).where(
                Content.organization_id == org.id, Content.deleted_at.is_(None)
            )
            total = (await self._db.execute(content_q)).scalar() or 0

            pub_q = select(func.count()).select_from(Content).where(
                Content.organization_id == org.id,
                Content.status == ContentStatus.PUBLISHED,
                Content.deleted_at.is_(None),
            )
            published = (await self._db.execute(pub_q)).scalar() or 0

            chan_q = select(func.count()).select_from(Channel).where(
                Channel.organization_id == org.id,
                Channel.status == ChannelStatus.ACTIVE,
            )
            channels = (await self._db.execute(chan_q)).scalar() or 0

            pend_q = select(func.count()).select_from(ApprovalRequest).where(
                ApprovalRequest.organization_id == org.id,
                ApprovalRequest.status.in_([ApprovalStatus.PENDING_REVIEW, ApprovalStatus.IN_REVIEW]),
            )
            pending = (await self._db.execute(pend_q)).scalar() or 0

            summaries.append(OrgSummaryItem(
                id=str(org.id),
                name=org.name,
                slug=org.slug,
                total_contents=total,
                published_contents=published,
                active_channels=channels,
                pending_approvals=pending,
            ))

        return summaries
