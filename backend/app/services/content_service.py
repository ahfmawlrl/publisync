"""Content business logic — S5 (F01)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

import structlog

from app.core.exceptions import ContentNotFoundError, WorkflowStateConflictError
from app.models.content import Content, ContentVersion, PublishResult
from app.models.enums import ContentStatus, PublishResultStatus
from app.repositories.content_repository import ContentRepository

if TYPE_CHECKING:
    from app.services.calendar_service import CalendarService

logger = structlog.get_logger()

# Valid state transitions
_VALID_TRANSITIONS: dict[ContentStatus, set[ContentStatus]] = {
    ContentStatus.DRAFT: {ContentStatus.PENDING_REVIEW, ContentStatus.SCHEDULED, ContentStatus.ARCHIVED},
    ContentStatus.PENDING_REVIEW: {ContentStatus.IN_REVIEW, ContentStatus.DRAFT},
    ContentStatus.IN_REVIEW: {ContentStatus.APPROVED, ContentStatus.REJECTED},
    ContentStatus.APPROVED: {ContentStatus.PUBLISHING, ContentStatus.SCHEDULED, ContentStatus.DRAFT},
    ContentStatus.REJECTED: {ContentStatus.DRAFT},
    ContentStatus.SCHEDULED: {ContentStatus.PUBLISHING, ContentStatus.CANCELLED, ContentStatus.DRAFT},
    ContentStatus.PUBLISHING: {
        ContentStatus.PUBLISHED, ContentStatus.PARTIALLY_PUBLISHED, ContentStatus.PUBLISH_FAILED,
    },
    ContentStatus.PUBLISHED: {ContentStatus.ARCHIVED},
    ContentStatus.PARTIALLY_PUBLISHED: {ContentStatus.PUBLISHING, ContentStatus.ARCHIVED},
    ContentStatus.PUBLISH_FAILED: {ContentStatus.PUBLISHING, ContentStatus.DRAFT, ContentStatus.ARCHIVED},
    ContentStatus.CANCELLED: {ContentStatus.DRAFT},
    ContentStatus.ARCHIVED: set(),
}


class ContentService:
    def __init__(
        self,
        repo: ContentRepository,
        calendar_service: CalendarService | None = None,
    ) -> None:
        self._repo = repo
        self._calendar = calendar_service

    async def _sync_calendar_create(
        self, org_id: UUID, content_id: UUID, title: str,
        scheduled_at: datetime, platforms: list[str] | None, user_id: UUID,
    ) -> None:
        """Create a calendar event for a scheduled content. Non-blocking — errors are logged, not raised."""
        if self._calendar is None:
            return
        try:
            await self._calendar.create_content_event(
                org_id=org_id,
                content_id=content_id,
                title=title,
                scheduled_at=scheduled_at,
                platforms=platforms,
                user_id=user_id,
            )
        except Exception:
            logger.warning(
                "calendar_sync_create_failed",
                content_id=str(content_id),
                exc_info=True,
            )

    async def _sync_calendar_update(
        self, content_id: UUID, org_id: UUID,
        title: str | None = None, scheduled_at: datetime | None = None,
    ) -> None:
        """Update the calendar event linked to a content. Non-blocking."""
        if self._calendar is None:
            return
        try:
            await self._calendar.update_content_event(
                content_id=content_id,
                org_id=org_id,
                title=title,
                scheduled_at=scheduled_at,
            )
        except Exception:
            logger.warning(
                "calendar_sync_update_failed",
                content_id=str(content_id),
                exc_info=True,
            )

    async def _sync_calendar_delete(self, content_id: UUID, org_id: UUID) -> None:
        """Delete calendar events linked to a content. Non-blocking."""
        if self._calendar is None:
            return
        try:
            await self._calendar.delete_content_events(content_id, org_id)
        except Exception:
            logger.warning(
                "calendar_sync_delete_failed",
                content_id=str(content_id),
                exc_info=True,
            )

    def _validate_transition(self, current: ContentStatus, target: ContentStatus) -> None:
        if target not in _VALID_TRANSITIONS.get(current, set()):
            raise WorkflowStateConflictError(
                f"Cannot transition from {current.value} to {target.value}"
            )

    async def create_content(
        self, org_id: UUID, author_id: UUID, data: dict
    ) -> Content:
        scheduled_at = None
        if data.get("scheduled_at"):
            scheduled_at = datetime.fromisoformat(data["scheduled_at"])

        channel_ids_raw = data.get("channel_ids", [])
        channel_ids = [UUID(cid) if isinstance(cid, str) else cid for cid in channel_ids_raw]

        content = Content(
            organization_id=org_id,
            title=data["title"],
            body=data.get("body"),
            status=ContentStatus.DRAFT,
            platforms=data.get("platforms", []),
            channel_ids=channel_ids,
            scheduled_at=scheduled_at,
            author_id=author_id,
            platform_contents=data.get("platform_contents"),
            metadata_=data.get("metadata"),
            ai_generated=data.get("ai_generated", False),
            media_urls=data.get("media_urls", []),
        )
        content = await self._repo.create(content)

        # Create initial version
        await self._repo.add_version(ContentVersion(
            content_id=content.id,
            organization_id=org_id,
            version=1,
            title=content.title,
            body=content.body,
            metadata_=content.metadata_,
            changed_by=author_id,
        ))

        # Sync: create calendar event if content has a scheduled time
        if scheduled_at is not None:
            await self._sync_calendar_create(
                org_id=org_id,
                content_id=content.id,
                title=content.title,
                scheduled_at=scheduled_at,
                platforms=content.platforms,
                user_id=author_id,
            )

        logger.info("content_created", content_id=str(content.id))
        return content

    async def get_content(self, content_id: UUID, org_id: UUID) -> Content:
        content = await self._repo.get_by_id(content_id)
        if content is None or content.organization_id != org_id:
            raise ContentNotFoundError()
        return content

    async def list_contents(
        self,
        org_id: UUID,
        page: int = 1,
        limit: int = 20,
        status: str | None = None,
        platform: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Content], int]:
        offset = (page - 1) * limit
        return await self._repo.list_contents(
            org_id, offset=offset, limit=limit, status=status, platform=platform, search=search
        )

    async def update_content(
        self, content_id: UUID, org_id: UUID, actor_id: UUID, data: dict
    ) -> Content:
        content = await self.get_content(content_id, org_id)

        if content.status not in (ContentStatus.DRAFT, ContentStatus.REJECTED):
            raise WorkflowStateConflictError("Content can only be edited in DRAFT or REJECTED status")

        old_scheduled_at = content.scheduled_at

        update_data: dict = {}
        if data.get("title") is not None:
            update_data["title"] = data["title"]
        if data.get("body") is not None:
            update_data["body"] = data["body"]
        if data.get("platforms") is not None:
            update_data["platforms"] = data["platforms"]
        if data.get("channel_ids") is not None:
            update_data["channel_ids"] = [UUID(cid) if isinstance(cid, str) else cid for cid in data["channel_ids"]]
        if data.get("scheduled_at") is not None:
            update_data["scheduled_at"] = datetime.fromisoformat(data["scheduled_at"]) if data["scheduled_at"] else None
        if data.get("platform_contents") is not None:
            update_data["platform_contents"] = data["platform_contents"]
        if data.get("media_urls") is not None:
            update_data["media_urls"] = data["media_urls"]
        if data.get("metadata") is not None:
            update_data["metadata_"] = data["metadata"]

        if update_data:
            content = await self._repo.update(content, update_data)

            # Create new version
            ver_num = await self._repo.get_latest_version_number(content_id) + 1
            await self._repo.add_version(ContentVersion(
                content_id=content.id,
                organization_id=org_id,
                version=ver_num,
                title=content.title,
                body=content.body,
                metadata_=content.metadata_,
                changed_by=actor_id,
            ))

        # Sync calendar: handle scheduled_at changes
        new_scheduled_at = content.scheduled_at
        if new_scheduled_at != old_scheduled_at:
            if new_scheduled_at is None and old_scheduled_at is not None:
                # Schedule removed → delete calendar event
                await self._sync_calendar_delete(content_id, org_id)
            elif new_scheduled_at is not None and old_scheduled_at is None:
                # Schedule added → create calendar event
                await self._sync_calendar_create(
                    org_id=org_id,
                    content_id=content_id,
                    title=content.title,
                    scheduled_at=new_scheduled_at,
                    platforms=content.platforms,
                    user_id=actor_id,
                )
            else:
                # Schedule changed → update calendar event
                await self._sync_calendar_update(
                    content_id=content_id,
                    org_id=org_id,
                    title=update_data.get("title"),
                    scheduled_at=new_scheduled_at,
                )
        elif "title" in update_data and new_scheduled_at is not None:
            # Title changed but schedule unchanged → update event title
            await self._sync_calendar_update(
                content_id=content_id,
                org_id=org_id,
                title=update_data["title"],
            )

        logger.info("content_updated", content_id=str(content_id))
        return content

    async def delete_content(self, content_id: UUID, org_id: UUID) -> None:
        content = await self.get_content(content_id, org_id)
        if content.status in (ContentStatus.PUBLISHING,):
            raise WorkflowStateConflictError("Cannot delete content while publishing")
        await self._repo.soft_delete(content)

        # Sync: remove associated calendar events
        await self._sync_calendar_delete(content_id, org_id)

        logger.info("content_deleted", content_id=str(content_id))

    async def save_draft(self, content_id: UUID, org_id: UUID, actor_id: UUID, data: dict) -> Content:
        content = await self.get_content(content_id, org_id)
        update_data: dict = {}
        if data.get("title") is not None:
            update_data["title"] = data["title"]
        if data.get("body") is not None:
            update_data["body"] = data["body"]
        if update_data:
            content = await self._repo.update(content, update_data)
        logger.info("content_draft_saved", content_id=str(content_id))
        return content

    async def request_review(self, content_id: UUID, org_id: UUID) -> Content:
        content = await self.get_content(content_id, org_id)
        self._validate_transition(content.status, ContentStatus.PENDING_REVIEW)
        content = await self._repo.update(content, {"status": ContentStatus.PENDING_REVIEW})
        logger.info("content_review_requested", content_id=str(content_id))
        return content

    async def get_publish_history(
        self, content_id: UUID, org_id: UUID, page: int = 1, limit: int = 50
    ) -> tuple[list[PublishResult], int]:
        await self.get_content(content_id, org_id)
        offset = (page - 1) * limit
        return await self._repo.list_publish_results(content_id, offset=offset, limit=limit)

    async def retry_publish(self, content_id: UUID, org_id: UUID) -> Content:
        content = await self.get_content(content_id, org_id)
        if content.status not in (ContentStatus.PUBLISH_FAILED, ContentStatus.PARTIALLY_PUBLISHED):
            raise WorkflowStateConflictError("Can only retry failed or partially published content")

        content = await self._repo.update(content, {"status": ContentStatus.PUBLISHING})
        # In production, this would trigger Celery task: publish_content.delay(str(content_id))
        logger.info("content_publish_retry", content_id=str(content_id))
        return content

    async def bulk_action(self, org_id: UUID, content_ids: list[UUID], action: str) -> int:
        count = 0
        for cid in content_ids:
            try:
                content = await self.get_content(cid, org_id)
                if action == "delete":
                    await self._repo.soft_delete(content)
                    await self._sync_calendar_delete(cid, org_id)
                    count += 1
                elif action == "archive":
                    if ContentStatus.ARCHIVED in _VALID_TRANSITIONS.get(content.status, set()):
                        await self._repo.update(content, {"status": ContentStatus.ARCHIVED})
                        count += 1
                elif action == "cancel_schedule":
                    if content.status == ContentStatus.SCHEDULED:
                        await self._repo.update(content, {
                            "status": ContentStatus.CANCELLED,
                            "scheduled_at": None,
                        })
                        await self._sync_calendar_delete(cid, org_id)
                        count += 1
            except Exception:
                continue
        logger.info("content_bulk_action", action=action, count=count)
        return count

    async def cancel_publish(self, content_id: UUID, org_id: UUID) -> Content:
        content = await self.get_content(content_id, org_id)
        if content.status != ContentStatus.SCHEDULED:
            raise WorkflowStateConflictError("Can only cancel scheduled content")
        content = await self._repo.update(content, {
            "status": ContentStatus.CANCELLED,
            "scheduled_at": None,
        })

        # Sync: remove calendar event for cancelled schedule
        await self._sync_calendar_delete(content_id, org_id)

        logger.info("content_publish_cancelled", content_id=str(content_id))
        return content

    async def determine_publish_status(self, content_id: UUID) -> ContentStatus:
        """Determine final content status based on publish results (PARTIALLY_PUBLISHED logic)."""
        counts = await self._repo.count_results_by_status(content_id)
        total = sum(counts.values())
        if total == 0:
            return ContentStatus.PUBLISH_FAILED

        success = counts.get(PublishResultStatus.SUCCESS.value, 0)
        if success == total:
            return ContentStatus.PUBLISHED
        elif success > 0:
            return ContentStatus.PARTIALLY_PUBLISHED
        else:
            return ContentStatus.PUBLISH_FAILED
