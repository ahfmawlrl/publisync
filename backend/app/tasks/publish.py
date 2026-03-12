"""Publish queue tasks — content publishing, retry, scheduled check."""

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import structlog
from celery import shared_task

logger = structlog.get_logger()


def _run_async(coro):
    """Run an async coroutine from a synchronous Celery task."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Celery worker 내부에서 이미 이벤트 루프가 실행 중인 경우
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


async def _do_publish(content_id: str, org_id: str) -> dict:
    """ContentService._execute_publish()를 호출하는 async 헬퍼."""
    from app.core.database import async_session_factory
    from app.repositories.content_repository import ContentRepository
    from app.services.content_service import ContentService

    async with async_session_factory() as session:
        # RLS 컨텍스트 설정
        await session.execute(
            __import__("sqlalchemy").text(f"SET LOCAL app.current_org_id = '{org_id}'")
        )

        repo = ContentRepository(session)
        service = ContentService(repo=repo)

        content = await repo.get_by_id(UUID(content_id))
        if not content:
            logger.error("publish_task_content_not_found", content_id=content_id)
            return {"content_id": content_id, "status": "not_found"}

        content = await service._execute_publish(content, UUID(org_id))
        await session.commit()

        return {
            "content_id": content_id,
            "status": content.status.value if hasattr(content.status, "value") else str(content.status),
        }


@shared_task(
    name="app.tasks.publish.publish_content",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
)
def publish_content(self, content_id: str, org_id: str) -> dict:
    """Publish content to all selected platforms.

    Uses PlatformAdapter for each channel, creates PublishResult records,
    and determines final content status (PUBLISHED / PARTIALLY_PUBLISHED / PUBLISH_FAILED).
    """
    logger.info("publish_content_start", content_id=content_id, org_id=org_id, attempt=self.request.retries)

    try:
        result = _run_async(_do_publish(content_id, org_id))
        logger.info("publish_content_done", **result)
        return result
    except Exception as exc:
        logger.error("publish_content_failed", content_id=content_id, error=str(exc))
        raise self.retry(exc=exc) from exc


@shared_task(name="app.tasks.publish.check_scheduled_contents")
def check_scheduled_contents() -> dict:
    """Check for contents with scheduled_at <= now and trigger publishing.

    Runs every 1 minute via Celery Beat.
    """
    logger.info("check_scheduled_contents_start")

    async def _check():
        from sqlalchemy import select, update

        from app.core.database import async_session_factory
        from app.models.content import Content
        from app.models.enums import ContentStatus

        triggered = 0
        async with async_session_factory() as session:
            now = datetime.now(UTC)
            stmt = select(Content).where(
                Content.status == ContentStatus.SCHEDULED,
                Content.scheduled_at <= now,
                Content.deleted_at.is_(None),
            )
            result = await session.execute(stmt)
            contents = list(result.scalars().all())

            for content in contents:
                await session.execute(
                    update(Content)
                    .where(Content.id == content.id)
                    .values(status=ContentStatus.PUBLISHING)
                )
                publish_content.delay(str(content.id), str(content.organization_id))
                triggered += 1

            await session.commit()
        return triggered

    try:
        triggered = _run_async(_check())
    except Exception as exc:
        logger.error("check_scheduled_error", error=str(exc))
        triggered = 0

    return {"checked_at": datetime.now(UTC).isoformat(), "triggered": triggered}


@shared_task(
    name="app.tasks.publish.retry_failed_publish",
    bind=True,
    max_retries=3,
)
def retry_failed_publish(self, content_id: str, org_id: str) -> dict:
    """Retry failed publish with exponential backoff (5m → 15m → 30m)."""
    retry_delays = [300, 900, 1800]  # 5 min, 15 min, 30 min
    current_delay = retry_delays[min(self.request.retries, len(retry_delays) - 1)]

    logger.info(
        "retry_failed_publish",
        content_id=content_id,
        attempt=self.request.retries,
        next_delay=current_delay,
    )

    try:
        return publish_content(content_id, org_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=current_delay) from exc
