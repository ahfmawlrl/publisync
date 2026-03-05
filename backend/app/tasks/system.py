"""System queue tasks — token refresh, cache management, cleanup."""

from datetime import UTC

import structlog
from celery import shared_task

logger = structlog.get_logger()


@shared_task(name="app.tasks.system.check_token_expiry")
def check_token_expiry() -> dict:
    """Check channels with tokens expiring within 1 hour and refresh them.

    Runs every 1 hour via Celery Beat.
    """
    from datetime import datetime

    logger.info("check_token_expiry_start")

    # In production, this would:
    # 1. Query channels WHERE status=ACTIVE AND token_expires_at < now + 1h
    # 2. For each channel:
    #    a. Update status to EXPIRING
    #    b. Attempt refresh_token via PlatformAdapter
    #    c. On success: update token, set ACTIVE
    #    d. On failure: set EXPIRED, record history

    return {
        "checked_at": datetime.now(UTC).isoformat(),
        "refreshed": 0,
        "expired": 0,
    }


@shared_task(name="app.tasks.system.refresh_dashboard_cache")
def refresh_dashboard_cache() -> dict:
    """Pre-compute dashboard data and cache in Redis.

    Runs every 5 minutes via Celery Beat.
    """
    logger.info("refresh_dashboard_cache_start")

    # In production, this would:
    # 1. For each active organization:
    #    a. Compute summary KPIs
    #    b. Cache with Redis SET cache:dashboard:{org_id}:summary TTL=5min
    # 2. Compute badge counts per user
    #    b. Cache with Redis SET cache:badges:{org_id} TTL=30s

    return {"organizations_cached": 0}


@shared_task(name="app.tasks.system.clean_expired_sessions")
def clean_expired_sessions() -> dict:
    """Clean expired refresh tokens and JWT blacklist entries.

    Runs every 6 hours via Celery Beat.
    """
    from datetime import datetime

    logger.info("clean_expired_sessions_start")

    # In production, this would:
    # 1. DELETE FROM refresh_tokens WHERE expires_at < now AND is_revoked = true
    # 2. Clean expired Redis JWT blacklist entries (auto-TTL handles this)
    # 3. DELETE FROM password_reset_tokens WHERE expires_at < now
    # 4. Update expired invitations: SET status='EXPIRED' WHERE expires_at < now

    return {"cleaned_at": datetime.now(UTC).isoformat()}


@shared_task(name="app.tasks.system.clean_deleted_media")
def clean_deleted_media() -> dict:
    """soft-delete 후 30일이 지난 미디어 에셋을 MinIO + DB에서 영구 삭제.

    Runs daily via Celery Beat.
    """
    import asyncio
    from datetime import datetime

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


@shared_task(name="app.tasks.system.check_storage_quota")
def check_storage_quota() -> dict:
    """기관별 스토리지 사용량을 점검하고, 80% 이상인 기관에 경고 로그 출력.

    Runs daily via Celery Beat.
    """
    import asyncio
    from datetime import datetime

    from sqlalchemy import select

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
