"""Content business logic — S5 (F01)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

import structlog

from app.core.exceptions import ContentNotFoundError, WorkflowStateConflictError
from app.models.approval import ApprovalHistory, ApprovalRequest
from app.models.content import Content, ContentVersion, PublishResult
from app.models.enums import ApprovalAction, ApprovalStatus, ContentStatus, PublishResultStatus
from app.repositories.approval_repository import ApprovalRepository
from app.repositories.content_repository import ContentRepository

logger = structlog.get_logger()


def _index_content_to_search(content: Content) -> None:
    """Index a content document to Meilisearch (best-effort, non-blocking)."""
    try:
        from app.integrations.search import index_document

        doc = {
            "id": str(content.id),
            "organization_id": str(content.organization_id),
            "title": content.title or "",
            "body": content.body or "",
            "status": content.status.value if hasattr(content.status, "value") else str(content.status),
            "platforms": content.platforms or [],
            "created_at": content.created_at.isoformat() if content.created_at else "",
            "updated_at": content.updated_at.isoformat() if content.updated_at else "",
        }
        index_document("contents", doc)
    except Exception as exc:
        structlog.get_logger().warning("search_index_content_failed", error=str(exc))


def _delete_content_from_search(content_id: UUID) -> None:
    """Remove a content document from Meilisearch (best-effort)."""
    try:
        from app.integrations.search import delete_document

        delete_document("contents", str(content_id))
    except Exception as exc:
        structlog.get_logger().warning("search_delete_content_failed", error=str(exc))

if TYPE_CHECKING:
    from app.services.calendar_service import CalendarService

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
        approval_repo: ApprovalRepository | None = None,
    ) -> None:
        self._repo = repo
        self._calendar = calendar_service
        self._approval_repo = approval_repo

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

        # Merge hashtags into metadata (no dedicated column yet)
        meta = dict(data.get("metadata") or {})
        hashtags = data.pop("hashtags", None)
        if hashtags:
            meta["hashtags"] = hashtags

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
            metadata_=meta or None,
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

        # Real-time search indexing (best-effort)
        _index_content_to_search(content)

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
        period: str | None = None,
    ) -> tuple[list[Content], int]:
        offset = (page - 1) * limit
        return await self._repo.list_contents(
            org_id, offset=offset, limit=limit, status=status, platform=platform, search=search, period=period
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
        if "scheduled_at" in data:
            update_data["scheduled_at"] = datetime.fromisoformat(data["scheduled_at"]) if data["scheduled_at"] else None
        if data.get("platform_contents") is not None:
            update_data["platform_contents"] = data["platform_contents"]
        if data.get("media_urls") is not None:
            update_data["media_urls"] = data["media_urls"]
        if data.get("metadata") is not None or data.get("hashtags") is not None:
            meta = dict(data.get("metadata") or content.metadata_ or {})
            if data.get("hashtags") is not None:
                meta["hashtags"] = data["hashtags"]
            update_data["metadata_"] = meta or None

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

        # Real-time search indexing (best-effort)
        _index_content_to_search(content)

        return content

    async def delete_content(self, content_id: UUID, org_id: UUID) -> None:
        content = await self.get_content(content_id, org_id)
        if content.status in (ContentStatus.PUBLISHING,):
            raise WorkflowStateConflictError("Cannot delete content while publishing")
        await self._repo.soft_delete(content)

        # Sync: remove associated calendar events
        await self._sync_calendar_delete(content_id, org_id)

        logger.info("content_deleted", content_id=str(content_id))

        # Remove from search index (best-effort)
        _delete_content_from_search(content_id)

    async def save_draft(self, content_id: UUID, org_id: UUID, actor_id: UUID, data: dict) -> Content:
        content = await self.get_content(content_id, org_id)
        update_data: dict = {}
        if data.get("title") is not None:
            update_data["title"] = data["title"]
        if data.get("body") is not None:
            update_data["body"] = data["body"]
        if data.get("platforms") is not None:
            update_data["platforms"] = data["platforms"]
        if data.get("media_urls") is not None:
            update_data["media_urls"] = data["media_urls"]
        if "scheduled_at" in data:
            update_data["scheduled_at"] = datetime.fromisoformat(data["scheduled_at"]) if data["scheduled_at"] else None
        if data.get("metadata") is not None or data.get("hashtags") is not None:
            meta = dict(data.get("metadata") or content.metadata_ or {})
            if data.get("hashtags") is not None:
                meta["hashtags"] = data["hashtags"]
            update_data["metadata_"] = meta or None
        if update_data:
            content = await self._repo.update(content, update_data)
        logger.info("content_draft_saved", content_id=str(content_id))
        return content

    async def request_review(self, content_id: UUID, org_id: UUID, requester_id: UUID | None = None) -> Content:
        content = await self.get_content(content_id, org_id)
        self._validate_transition(content.status, ContentStatus.PENDING_REVIEW)
        content = await self._repo.update(content, {"status": ContentStatus.PENDING_REVIEW})

        # Create ApprovalRequest record so the approval list shows this item
        if self._approval_repo is not None:
            approval_request = ApprovalRequest(
                content_id=content_id,
                organization_id=org_id,
                status=ApprovalStatus.PENDING_REVIEW,
                requested_by=requester_id or content.author_id,
            )
            approval_request = await self._approval_repo.create(approval_request)

            # Add initial history entry (SUBMIT action)
            await self._approval_repo.add_history(ApprovalHistory(
                request_id=approval_request.id,
                organization_id=org_id,
                step=0,
                action=ApprovalAction.SUBMIT,
                reviewer_id=requester_id or content.author_id,
            ))

        logger.info("content_review_requested", content_id=str(content_id))
        return content

    async def get_publish_history(
        self, content_id: UUID, org_id: UUID, page: int = 1, limit: int = 50
    ) -> tuple[list[PublishResult], int]:
        await self.get_content(content_id, org_id)
        offset = (page - 1) * limit
        return await self._repo.list_publish_results(content_id, offset=offset, limit=limit)

    async def publish(self, content_id: UUID, org_id: UUID) -> Content:
        """APPROVED 상태의 콘텐츠를 게시(PUBLISHING → PUBLISHED) 처리한다."""
        content = await self.get_content(content_id, org_id)
        if content.status != ContentStatus.APPROVED:
            raise WorkflowStateConflictError("Can only publish approved content")

        content = await self._repo.update(content, {"status": ContentStatus.PUBLISHING})
        logger.info("content_publish_started", content_id=str(content_id))

        # 채널 미연동 환경에서는 바로 PUBLISHED로 전환 (데모/테스트 Fallback)
        channel_ids = content.channel_ids or []
        if not channel_ids:
            content = await self._repo.update(content, {"status": ContentStatus.PUBLISHED})
            logger.info("content_published_no_channels", content_id=str(content_id))
            return content

        # 실제 채널이 있으면 각 플랫폼에 게시 실행
        content = await self._execute_publish(content, org_id)
        return content

    async def _execute_publish(self, content: Content, org_id: UUID) -> Content:
        """각 채널에 대해 플랫폼 어댑터를 호출하여 실제 게시를 수행한다.

        각 채널별 PublishResult 레코드를 생성하고,
        전체 결과에 따라 최종 상태(PUBLISHED/PARTIALLY_PUBLISHED/PUBLISH_FAILED)를 결정한다.
        """
        from uuid import UUID as UUIDType

        from app.core.encryption import decrypt_token
        from app.integrations.platforms import get_adapter
        from app.models.channel import Channel

        channel_ids = content.channel_ids or []
        db = self._repo._db

        for ch_id in channel_ids:
            ch_uuid = ch_id if isinstance(ch_id, UUIDType) else UUIDType(str(ch_id))
            channel = await db.get(Channel, ch_uuid)

            if not channel:
                logger.warning("publish_channel_not_found", channel_id=str(ch_id))
                # PublishResult FAILED 기록
                pr = PublishResult(
                    content_id=content.id,
                    organization_id=org_id,
                    channel_id=ch_uuid,
                    status=PublishResultStatus.FAILED,
                    error_message=f"Channel {ch_id} not found",
                )
                db.add(pr)
                continue

            # 토큰 복호화
            try:
                access_token = decrypt_token(channel.access_token_enc) if channel.access_token_enc else ""
            except Exception as exc:
                logger.error("publish_token_decrypt_failed", channel_id=str(ch_id), error=str(exc))
                pr = PublishResult(
                    content_id=content.id,
                    organization_id=org_id,
                    channel_id=ch_uuid,
                    status=PublishResultStatus.FAILED,
                    error_message=f"Token decrypt failed: {exc!s}",
                )
                db.add(pr)
                continue

            # 플랫폼 어댑터 호출
            adapter = get_adapter(channel.platform)
            content_data = {
                "title": content.title,
                "body": content.body or "",
                "media_urls": content.media_urls or [],
                "channel_account_id": channel.platform_account_id,
                "platforms": content.platforms or [],
            }

            try:
                result = await adapter.publish(access_token, content_data)
            except Exception as exc:
                logger.error("publish_adapter_error", channel_id=str(ch_id), error=str(exc))
                result = None

            if result and result.success:
                pr = PublishResult(
                    content_id=content.id,
                    organization_id=org_id,
                    channel_id=ch_uuid,
                    status=PublishResultStatus.SUCCESS,
                    platform_post_id=result.platform_post_id,
                    platform_url=result.platform_url,
                )
                logger.info(
                    "publish_channel_success",
                    channel_id=str(ch_id),
                    platform=channel.platform.value,
                    platform_post_id=result.platform_post_id,
                )
            else:
                error_msg = result.error_message if result else "Unknown adapter error"
                pr = PublishResult(
                    content_id=content.id,
                    organization_id=org_id,
                    channel_id=ch_uuid,
                    status=PublishResultStatus.FAILED,
                    error_message=error_msg,
                )
                logger.warning(
                    "publish_channel_failed",
                    channel_id=str(ch_id),
                    platform=channel.platform.value,
                    error=error_msg,
                )

            db.add(pr)

        await db.flush()

        # 최종 상태 결정
        final_status = await self.determine_publish_status(content.id)
        content = await self._repo.update(content, {"status": final_status})
        logger.info(
            "publish_completed",
            content_id=str(content.id),
            final_status=final_status.value,
        )
        return content

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
