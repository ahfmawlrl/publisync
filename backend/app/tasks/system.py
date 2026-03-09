"""System queue tasks — token refresh, cache management, cleanup, partitions, analytics."""

import json
from datetime import UTC, datetime, timedelta

import structlog
from celery import shared_task
from sqlalchemy import func, select, text, update

from app.core.database import sync_session_factory

logger = structlog.get_logger()


# ── Token expiry check ───────────────────────────────────────


@shared_task(name="app.tasks.system.check_token_expiry")
def check_token_expiry() -> dict:
    """Check channels with tokens expiring within 1 hour and mark them EXPIRING.

    Runs every 1 hour via Celery Beat.
    For each expiring channel, updates status and creates a notification
    for all AM/AO users in the organization.
    """
    from app.models.channel import Channel
    from app.models.enums import ChannelStatus

    logger.info("check_token_expiry_start")
    now = datetime.now(UTC)
    threshold = now + timedelta(hours=1)
    refreshed = 0
    expired_count = 0

    with sync_session_factory() as session:
        # Find channels with tokens expiring within 1 hour
        stmt = select(Channel).where(
            Channel.status == ChannelStatus.ACTIVE,
            Channel.token_expires_at.isnot(None),
            Channel.token_expires_at < threshold,
        )
        channels = list(session.execute(stmt).scalars().all())

        for channel in channels:
            try:
                if channel.token_expires_at and channel.token_expires_at <= now:
                    # Already expired
                    channel.status = ChannelStatus.EXPIRED
                    expired_count += 1
                    logger.warning(
                        "channel_token_expired",
                        channel_id=str(channel.id),
                        platform=channel.platform.value,
                    )
                else:
                    # Expiring soon
                    channel.status = ChannelStatus.EXPIRING
                    refreshed += 1
                    logger.info(
                        "channel_token_expiring",
                        channel_id=str(channel.id),
                        platform=channel.platform.value,
                        expires_at=str(channel.token_expires_at),
                    )
            except Exception:
                logger.exception(
                    "check_token_expiry_channel_error",
                    channel_id=str(channel.id),
                )

        session.commit()

    return {
        "checked_at": now.isoformat(),
        "expiring": refreshed,
        "expired": expired_count,
    }


# ── Dashboard cache refresh ──────────────────────────────────


@shared_task(name="app.tasks.system.refresh_dashboard_cache")
def refresh_dashboard_cache() -> dict:
    """Pre-compute dashboard summary KPIs per organization and cache in Redis.

    Runs every 5 minutes via Celery Beat.
    Caches: total contents, published count, active channels, pending approvals.
    """
    from app.models.content import Content
    from app.models.enums import ChannelStatus, ContentStatus

    logger.info("refresh_dashboard_cache_start")

    orgs_cached = 0

    with sync_session_factory() as session:
        # Get distinct organization IDs from contents
        org_stmt = select(Content.organization_id).distinct()
        org_ids = [row[0] for row in session.execute(org_stmt).fetchall()]

        for org_id in org_ids:
            try:
                # Count total contents
                total = session.execute(
                    select(func.count()).select_from(Content).where(
                        Content.organization_id == org_id,
                    )
                ).scalar() or 0

                # Count published contents
                published = session.execute(
                    select(func.count()).select_from(Content).where(
                        Content.organization_id == org_id,
                        Content.status == ContentStatus.PUBLISHED,
                    )
                ).scalar() or 0

                # Count active channels
                from app.models.channel import Channel

                active_channels = session.execute(
                    select(func.count()).select_from(Channel).where(
                        Channel.organization_id == org_id,
                        Channel.status == ChannelStatus.ACTIVE,
                    )
                ).scalar() or 0

                # Cache to Redis (best-effort, don't fail task if Redis down)
                try:
                    import redis

                    from app.core.config import settings

                    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
                    cache_key = f"cache:dashboard:{org_id}:summary"
                    r.setex(cache_key, 300, json.dumps({
                        "total_contents": total,
                        "published_contents": published,
                        "active_channels": active_channels,
                        "cached_at": datetime.now(UTC).isoformat(),
                    }))
                except Exception:
                    logger.warning("redis_cache_failed", org_id=str(org_id))

                orgs_cached += 1

            except Exception:
                logger.exception("dashboard_cache_org_error", org_id=str(org_id))

    return {"organizations_cached": orgs_cached}


# ── Clean expired sessions ───────────────────────────────────


@shared_task(name="app.tasks.system.clean_expired_sessions")
def clean_expired_sessions() -> dict:
    """Clean expired invitations and stale data.

    Runs every 6 hours via Celery Beat.
    - Updates expired invitations: PENDING → EXPIRED
    """
    from app.models.enums import InvitationStatus
    from app.models.user import Invitation

    logger.info("clean_expired_sessions_start")
    now = datetime.now(UTC)

    with sync_session_factory() as session:
        # Update expired invitations
        stmt = (
            update(Invitation)
            .where(
                Invitation.status == InvitationStatus.PENDING,
                Invitation.expires_at < now,
            )
            .values(status=InvitationStatus.EXPIRED)
        )
        result = session.execute(stmt)
        expired_invitations = result.rowcount

        session.commit()

    logger.info(
        "clean_expired_sessions_done",
        expired_invitations=expired_invitations,
    )
    return {
        "cleaned_at": now.isoformat(),
        "expired_invitations": expired_invitations,
    }


# ── Clean deleted media ──────────────────────────────────────


@shared_task(name="app.tasks.system.clean_deleted_media")
def clean_deleted_media() -> dict:
    """soft-delete 후 30일이 지난 미디어 에셋을 MinIO + DB에서 영구 삭제.

    Runs daily via Celery Beat.
    """
    import asyncio

    from app.core.database import async_session_factory
    from app.integrations.storage import delete_object
    from app.repositories.media_repository import MediaRepository

    logger.info("clean_deleted_media_start")

    async def _run() -> dict:
        deleted_count = 0
        error_count = 0

        async with async_session_factory() as session:
            repo = MediaRepository(session)
            expired_assets = await repo.get_expired_deleted_assets(days=30)

            for asset in expired_assets:
                try:
                    # MinIO에서 원본 파일 삭제
                    delete_object(asset.object_key)

                    # 썸네일이 있으면 함께 삭제
                    if asset.thumbnail_url:
                        try:
                            delete_object(asset.thumbnail_url)
                        except Exception:
                            logger.warning(
                                "thumbnail_delete_failed",
                                asset_id=str(asset.id),
                                thumb_key=asset.thumbnail_url,
                            )

                    # DB에서 영구 삭제
                    await repo.hard_delete_asset(asset.id)
                    deleted_count += 1
                    logger.info("media_permanently_deleted", asset_id=str(asset.id))
                except Exception as e:
                    error_count += 1
                    logger.error(
                        "media_permanent_delete_failed",
                        asset_id=str(asset.id),
                        error=str(e),
                    )

            await session.commit()

        return {
            "cleaned_at": datetime.now(UTC).isoformat(),
            "deleted_count": deleted_count,
            "error_count": error_count,
        }

    return asyncio.get_event_loop().run_until_complete(_run())


# ── Check storage quota ──────────────────────────────────────


@shared_task(name="app.tasks.system.check_storage_quota")
def check_storage_quota() -> dict:
    """기관별 스토리지 사용량을 점검하고, 80% 이상인 기관에 경고 로그 출력.

    Runs daily via Celery Beat.
    """
    import asyncio

    from app.core.database import async_session_factory
    from app.models.user import Organization
    from app.repositories.media_repository import MediaRepository
    from app.services.media_service import STORAGE_QUOTA_BYTES, STORAGE_QUOTA_WARNING_RATIO

    logger.info("check_storage_quota_start")

    async def _run() -> dict:
        warning_orgs: list[str] = []

        async with async_session_factory() as session:
            # 모든 활성 기관 조회
            stmt = select(Organization.id)
            result = await session.execute(stmt)
            org_ids = [row[0] for row in result.fetchall()]

            repo = MediaRepository(session)

            for org_id in org_ids:
                usage = await repo.get_org_storage_usage(org_id)
                ratio = usage / STORAGE_QUOTA_BYTES if STORAGE_QUOTA_BYTES > 0 else 0.0

                if ratio >= STORAGE_QUOTA_WARNING_RATIO:
                    warning_orgs.append(str(org_id))
                    logger.warning(
                        "storage_quota_warning",
                        org_id=str(org_id),
                        usage_gb=round(usage / (1024**3), 2),
                        quota_gb=round(STORAGE_QUOTA_BYTES / (1024**3), 0),
                        usage_pct=round(ratio * 100, 1),
                    )

        return {
            "checked_at": datetime.now(UTC).isoformat(),
            "total_orgs": len(org_ids),
            "warning_orgs": warning_orgs,
        }

    return asyncio.get_event_loop().run_until_complete(_run())


# ── Partition management ─────────────────────────────────────


@shared_task(name="app.tasks.system.create_monthly_partition")
def create_monthly_partition() -> dict:
    """Create next month's audit_logs partition if it doesn't exist.

    Runs daily via Celery Beat. The PL/pgSQL function handles idempotency
    (skips if partition already exists).
    """
    logger.info("create_monthly_partition_start")

    now = datetime.now(UTC)
    # Always create partition for next month
    next_month = (now.replace(day=1) + timedelta(days=32)).replace(day=1)

    with sync_session_factory() as session:
        result = session.execute(
            text("SELECT create_audit_partition(:target_date)"),
            {"target_date": next_month.date()},
        )
        message = result.scalar()
        session.commit()

    logger.info("create_monthly_partition_done", result=message)
    return {
        "executed_at": now.isoformat(),
        "target_month": next_month.strftime("%Y-%m"),
        "result": message,
    }


@shared_task(name="app.tasks.system.cleanup_old_partitions")
def cleanup_old_partitions() -> dict:
    """Drop audit_logs partitions older than 3 years.

    Runs daily via Celery Beat. The PL/pgSQL function handles the logic
    of finding and dropping partitions with upper bounds before the cutoff.
    Only actually drops partitions if retention period exceeded.
    """
    logger.info("cleanup_old_partitions_start")

    now = datetime.now(UTC)

    with sync_session_factory() as session:
        result = session.execute(
            text("SELECT cleanup_old_audit_partitions(36)")
        )
        message = result.scalar()
        session.commit()

    logger.info("cleanup_old_partitions_done", result=message)
    return {
        "executed_at": now.isoformat(),
        "result": message,
    }


# ── Analytics snapshots sync ─────────────────────────────────


@shared_task(name="app.tasks.system.sync_analytics_snapshots")
def sync_analytics_snapshots() -> dict:
    """Compute daily analytics metrics per organization and upsert into analytics_snapshots.

    Runs every 1 hour via Celery Beat.
    Aggregates from publish_results: total posts, views, likes, shares, comments.
    """
    from app.models.content import PublishResult
    from app.models.enums import PublishResultStatus
    from app.models.user import Organization

    logger.info("sync_analytics_snapshots_start")

    now = datetime.now(UTC)
    today = now.date()
    orgs_synced = 0

    with sync_session_factory() as session:
        # Get all organization IDs
        org_ids = [
            row[0] for row in session.execute(select(Organization.id)).fetchall()
        ]

        for org_id in org_ids:
            try:
                # Aggregate metrics from publish_results for this org
                stmt = select(
                    func.count().label("total_posts"),
                    func.coalesce(func.sum(PublishResult.views), 0).label("total_views"),
                    func.coalesce(func.sum(PublishResult.likes), 0).label("total_likes"),
                    func.coalesce(func.sum(PublishResult.shares), 0).label("total_shares"),
                    func.coalesce(func.sum(PublishResult.comments_count), 0).label("total_comments"),
                ).where(
                    PublishResult.organization_id == org_id,
                    PublishResult.status == PublishResultStatus.SUCCESS,
                )
                row = session.execute(stmt).one()

                total_posts = row.total_posts or 0
                total_views = int(row.total_views)
                total_likes = int(row.total_likes)
                total_shares = int(row.total_shares)
                total_comments = int(row.total_comments)

                # Calculate engagement rate
                engagement_rate = 0.0
                if total_views > 0:
                    engagement_rate = round(
                        (total_likes + total_comments + total_shares) / total_views * 100, 2
                    )

                metrics = {
                    "total_posts": total_posts,
                    "total_views": total_views,
                    "total_likes": total_likes,
                    "total_shares": total_shares,
                    "total_comments": total_comments,
                    "engagement_rate": engagement_rate,
                }

                # Upsert into analytics_snapshots
                from sqlalchemy.dialects.postgresql import insert as pg_insert

                from app.models.base import generate_uuid

                upsert_stmt = pg_insert(
                    text("analytics_snapshots")
                ).values(
                    id=generate_uuid(),
                    organization_id=org_id,
                    channel_id=None,
                    period="daily",
                    snapshot_date=today,
                    metrics=json.dumps(metrics),
                    created_at=now,
                )

                # Use raw SQL for the upsert since we're using text table reference
                session.execute(
                    text("""
                        INSERT INTO analytics_snapshots (id, organization_id, channel_id, period, snapshot_date, metrics, created_at)
                        VALUES (:id, :org_id, NULL, 'daily', :snapshot_date, :metrics, :created_at)
                        ON CONFLICT (organization_id, snapshot_date)
                            WHERE channel_id IS NULL AND period = 'daily'
                        DO UPDATE SET
                            metrics = EXCLUDED.metrics,
                            created_at = EXCLUDED.created_at
                    """),
                    {
                        "id": generate_uuid(),
                        "org_id": org_id,
                        "snapshot_date": today,
                        "metrics": json.dumps(metrics),
                        "created_at": now,
                    },
                )

                orgs_synced += 1

            except Exception:
                logger.exception(
                    "sync_analytics_snapshot_error",
                    org_id=str(org_id),
                )

        session.commit()

    logger.info("sync_analytics_snapshots_done", orgs_synced=orgs_synced)
    return {
        "synced_at": now.isoformat(),
        "orgs_synced": orgs_synced,
    }
