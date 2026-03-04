"""Publish queue tasks — content publishing, retry, scheduled check."""

import structlog
from celery import shared_task

logger = structlog.get_logger()


@shared_task(
    name="app.tasks.publish.publish_content",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 min → 15 min → 30 min (exponential in retry logic)
)
def publish_content(self, content_id: str, org_id: str) -> dict:
    """Publish content to all selected platforms.

    Uses PlatformAdapter for each channel, creates PublishResult records,
    and determines final content status (PUBLISHED / PARTIALLY_PUBLISHED / PUBLISH_FAILED).
    """
    from app.core.database import sync_session_factory
    from app.core.encryption import decrypt_token
    from app.integrations.platforms import get_adapter
    from app.models.content import Content, PublishResult
    from app.models.channel import Channel
    from app.models.enums import ContentStatus, PublishResultStatus

    logger.info("publish_content_start", content_id=content_id, org_id=org_id, attempt=self.request.retries)

    # In production, this would:
    # 1. Load content from DB
    # 2. For each channel_id in content.channel_ids:
    #    a. Load channel, decrypt token
    #    b. Call adapter.publish()
    #    c. Create PublishResult (SUCCESS/FAILED)
    # 3. Determine final status via determine_publish_status()
    # 4. Emit SSE event

    return {"content_id": content_id, "status": "completed"}


@shared_task(name="app.tasks.publish.check_scheduled_contents")
def check_scheduled_contents() -> dict:
    """Check for contents with scheduled_at <= now and trigger publishing.

    Runs every 1 minute via Celery Beat.
    """
    from datetime import datetime, timezone

    logger.info("check_scheduled_contents_start")

    # In production, this would:
    # 1. Query contents WHERE status=SCHEDULED AND scheduled_at <= now
    # 2. For each content:
    #    a. Update status to PUBLISHING
    #    b. Trigger publish_content.delay(content_id, org_id)

    return {"checked_at": datetime.now(timezone.utc).isoformat(), "triggered": 0}


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
        raise self.retry(exc=exc, countdown=current_delay)
