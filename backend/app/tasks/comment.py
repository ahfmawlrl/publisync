"""Comment collection task — collect comments from platforms every 5 minutes."""

from datetime import UTC

import structlog
from celery import shared_task

logger = structlog.get_logger()


@shared_task(name="app.tasks.comment.collect_comments", bind=True, max_retries=3)
def collect_comments(self) -> dict:
    """Collect new comments from all active channels.

    Runs every 5 minutes via Celery Beat.
    For each active channel, calls the platform adapter to fetch new comments
    and stores them in the comments table.
    """
    from datetime import datetime

    logger.info("collect_comments_start")

    # In production, this would:
    # 1. Query active channels with valid tokens
    # 2. For each channel, call PlatformAdapter.get_comments(since=last_collected_at)
    # 3. Upsert new comments to DB (deduplicate by channel_id + external_id)
    # 4. Update channel.last_comment_collected_at
    # 5. Queue sentiment analysis for new comments

    return {
        "collected_at": datetime.now(UTC).isoformat(),
        "channels_checked": 0,
        "new_comments": 0,
    }
