"""Comment collection task — collect comments from platforms every 5 minutes."""

import asyncio
from datetime import UTC, datetime

import structlog
from celery import shared_task
from sqlalchemy import select

from app.core.database import sync_session_factory
from app.core.encryption import decrypt_token
from app.integrations.platforms import get_adapter
from app.models.channel import Channel
from app.models.comment import Comment
from app.models.enums import ChannelStatus

logger = structlog.get_logger()


def _run_async(coro):
    """Run an async coroutine from synchronous Celery context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(name="app.tasks.comment.collect_comments", bind=True, max_retries=3)
def collect_comments(self) -> dict:
    """Collect new comments from all active channels.

    Runs every 5 minutes via Celery Beat.
    For each active channel, calls the platform adapter to fetch new comments
    and upserts them into the comments table (deduplicate by channel_id + external_id).
    """
    logger.info("collect_comments_start")

    channels_checked = 0
    new_comments_total = 0
    errors = 0

    with sync_session_factory() as session:
        # 1. Query active channels with valid tokens
        stmt = select(Channel).where(
            Channel.status == ChannelStatus.ACTIVE,
            Channel.access_token_enc.isnot(None),
        )
        channels = list(session.execute(stmt).scalars().all())

        for channel in channels:
            channels_checked += 1
            try:
                access_token = decrypt_token(channel.access_token_enc)
                adapter = get_adapter(channel.platform)

                # 2. Fetch comments (paginate until exhausted)
                all_comments = []
                page_token = None
                since = channel.last_comment_collected_at

                while True:
                    fetched, next_page = _run_async(
                        adapter.get_comments(
                            access_token=access_token,
                            channel_id=channel.platform_account_id,
                            since=since,
                            page_token=page_token,
                            max_results=100,
                        )
                    )
                    all_comments.extend(fetched)
                    if not next_page:
                        break
                    page_token = next_page

                # 3. Upsert new comments (deduplicate by channel_id + external_id)
                for comment_data in all_comments:
                    existing = session.execute(
                        select(Comment).where(
                            Comment.channel_id == channel.id,
                            Comment.external_id == comment_data.external_id,
                        )
                    ).scalar_one_or_none()

                    if existing is not None:
                        continue

                    comment = Comment(
                        organization_id=channel.organization_id,
                        channel_id=channel.id,
                        platform=channel.platform,
                        external_id=comment_data.external_id,
                        text=comment_data.text,
                        author_name=comment_data.author_name,
                        author_profile_url=comment_data.author_profile_url,
                        platform_created_at=comment_data.platform_created_at,
                    )
                    session.add(comment)
                    new_comments_total += 1

                # 4. Update last_comment_collected_at
                channel.last_comment_collected_at = datetime.now(UTC)
                session.flush()

                logger.info(
                    "collect_comments_channel_done",
                    channel_id=str(channel.id),
                    platform=channel.platform.value,
                    fetched=len(all_comments),
                    new=new_comments_total,
                )

            except Exception:
                errors += 1
                logger.exception(
                    "collect_comments_channel_error",
                    channel_id=str(channel.id),
                    platform=channel.platform.value,
                )
                continue

        session.commit()

    result = {
        "collected_at": datetime.now(UTC).isoformat(),
        "channels_checked": channels_checked,
        "new_comments": new_comments_total,
        "errors": errors,
    }
    logger.info("collect_comments_done", **result)
    return result
