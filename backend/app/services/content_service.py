"""Content business logic — S5 (F01)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

import structlog

from app.core.exceptions import ContentNotFoundError, NotFoundError, WorkflowStateConflictError
from app.models.approval import ApprovalHistory, ApprovalRequest
from app.models.content import Content, ContentVariant, ContentVersion, PublishResult, VariantMedia
from app.models.enums import (
    ApprovalAction,
    ApprovalStatus,
    ContentStatus,
    MediaRoleType,
    PlatformType,
    PublishResultStatus,
)
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

        # v2.0: source_media_id
        source_media_id = None
        if data.get("source_media_id"):
            raw = data["source_media_id"]
            source_media_id = UUID(raw) if isinstance(raw, str) else raw

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
            source_media_id=source_media_id,
        )
        content = await self._repo.create(content)

        # v2.0: Create variants from inline data or uniform_publish
        await self._create_variants_from_request(content, org_id, data)

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
        """APPROVED 상태의 콘텐츠를 게시(PUBLISHING -> PUBLISHED) 처리한다.

        v2.0: variants가 있으면 variant 기반 게시, 없으면 레거시 channel_ids 기반.
        """
        content = await self.get_content(content_id, org_id)
        if content.status != ContentStatus.APPROVED:
            raise WorkflowStateConflictError("Can only publish approved content")

        content = await self._repo.update(content, {"status": ContentStatus.PUBLISHING})
        logger.info("content_publish_started", content_id=str(content_id))

        variants = content.variants or []
        channel_ids = content.channel_ids or []

        if not variants and not channel_ids:
            # 채널/variant 모두 없으면 데모 Fallback
            content = await self._repo.update(content, {"status": ContentStatus.PUBLISHED})
            logger.info("content_published_no_channels", content_id=str(content_id))
            return content

        content = await self._execute_publish(content, org_id)
        return content

    async def _execute_publish(self, content: Content, org_id: UUID) -> Content:
        """v2.0: variant 기반 게시. variant 없으면 레거시 channel_ids fallback.

        각 variant(또는 채널)별 PublishResult 레코드를 생성하고,
        전체 결과에 따라 최종 상태를 결정한다.
        """
        from uuid import UUID as UUIDType

        db = self._repo._db
        variants = content.variants or []

        if variants:
            # v2.0: variant 기반 게시
            for variant in variants:
                ch_uuid = variant.channel_id
                if not ch_uuid:
                    # channel_id 없는 variant는 건너뜀
                    logger.warning("publish_variant_no_channel", variant_id=str(variant.id))
                    continue

                await self._publish_to_channel(
                    db, content, org_id, ch_uuid, variant=variant,
                )
        else:
            # 레거시: channel_ids 기반
            for ch_id in content.channel_ids or []:
                ch_uuid = ch_id if isinstance(ch_id, UUIDType) else UUIDType(str(ch_id))
                await self._publish_to_channel(db, content, org_id, ch_uuid)

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

    async def _publish_to_channel(
        self,
        db,
        content: Content,
        org_id: UUID,
        channel_id: UUID,
        variant: ContentVariant | None = None,
    ) -> None:
        """Publish to a single channel, creating a PublishResult record."""
        from app.core.encryption import decrypt_token
        from app.integrations.platforms import get_adapter
        from app.models.channel import Channel

        channel = await db.get(Channel, channel_id)
        if not channel:
            logger.warning("publish_channel_not_found", channel_id=str(channel_id))
            db.add(PublishResult(
                content_id=content.id,
                organization_id=org_id,
                channel_id=channel_id,
                variant_id=variant.id if variant else None,
                status=PublishResultStatus.FAILED,
                error_message=f"Channel {channel_id} not found",
            ))
            return

        # 토큰 복호화
        try:
            access_token = decrypt_token(channel.access_token_enc) if channel.access_token_enc else ""
        except Exception as exc:
            logger.error("publish_token_decrypt_failed", channel_id=str(channel_id), error=str(exc))
            db.add(PublishResult(
                content_id=content.id,
                organization_id=org_id,
                channel_id=channel_id,
                variant_id=variant.id if variant else None,
                status=PublishResultStatus.FAILED,
                error_message=f"Token decrypt failed: {exc!s}",
            ))
            return

        # v2.0: variant 데이터 우선, fallback to content
        title = (variant.title if variant and variant.title else content.title) or ""
        body = (variant.body if variant and variant.body else content.body) or ""

        adapter = get_adapter(channel.platform)
        content_data = {
            "title": title,
            "body": body,
            "media_urls": content.media_urls or [],
            "channel_account_id": channel.platform_account_id,
            "platforms": content.platforms or [],
        }

        try:
            result = await adapter.publish(access_token, content_data)
        except Exception as exc:
            logger.error("publish_adapter_error", channel_id=str(channel_id), error=str(exc))
            result = None

        if result and result.success:
            pr = PublishResult(
                content_id=content.id,
                organization_id=org_id,
                channel_id=channel_id,
                variant_id=variant.id if variant else None,
                status=PublishResultStatus.SUCCESS,
                platform_post_id=result.platform_post_id,
                platform_url=result.platform_url,
            )
            logger.info(
                "publish_channel_success",
                channel_id=str(channel_id),
                platform=channel.platform.value,
                platform_post_id=result.platform_post_id,
            )
        else:
            error_msg = result.error_message if result else "Unknown adapter error"
            pr = PublishResult(
                content_id=content.id,
                organization_id=org_id,
                channel_id=channel_id,
                variant_id=variant.id if variant else None,
                status=PublishResultStatus.FAILED,
                error_message=error_msg,
            )
            logger.warning(
                "publish_channel_failed",
                channel_id=str(channel_id),
                platform=channel.platform.value,
                error=error_msg,
            )

        db.add(pr)

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

    # ── Variant CRUD (v2.0) ─────────────────────────────

    async def _create_variants_from_request(
        self, content: Content, org_id: UUID, data: dict,
    ) -> None:
        """Create variants from inline request data or uniform_publish mode."""
        variants_data = data.get("variants")
        uniform = data.get("uniform_publish", False)

        if variants_data:
            # Explicit variant definitions
            for vd in variants_data:
                variant = ContentVariant(
                    content_id=content.id,
                    organization_id=org_id,
                    platform=PlatformType(vd["platform"]),
                    channel_id=UUID(vd["channel_id"]) if vd.get("channel_id") else None,
                    title=vd.get("title"),
                    body=vd.get("body"),
                    hashtags=vd.get("hashtags"),
                    metadata_=vd.get("metadata"),
                    sort_order=vd.get("sort_order", 0),
                )
                await self._repo.create_variant(variant)
        elif uniform and data.get("channel_ids"):
            # Uniform publish: create identical variants per channel
            channel_ids = data.get("channel_ids", [])
            platforms = data.get("platforms", [])
            for ch_id_raw in channel_ids:
                ch_id = UUID(ch_id_raw) if isinstance(ch_id_raw, str) else ch_id_raw
                # Determine platform from channel (best-effort: use first platform or look up)
                platform = platforms[0] if platforms else "YOUTUBE"
                variant = ContentVariant(
                    content_id=content.id,
                    organization_id=org_id,
                    platform=PlatformType(platform.upper()),
                    channel_id=ch_id,
                    sort_order=0,
                )
                await self._repo.create_variant(variant)

    async def create_variant(
        self, content_id: UUID, org_id: UUID, data: dict,
    ) -> ContentVariant:
        """Add a variant to an existing content."""
        await self.get_content(content_id, org_id)
        variant = ContentVariant(
            content_id=content_id,
            organization_id=org_id,
            platform=PlatformType(data["platform"]),
            channel_id=UUID(data["channel_id"]) if data.get("channel_id") else None,
            title=data.get("title"),
            body=data.get("body"),
            hashtags=data.get("hashtags"),
            metadata_=data.get("metadata"),
            sort_order=data.get("sort_order", 0),
        )
        return await self._repo.create_variant(variant)

    async def list_variants(self, content_id: UUID, org_id: UUID) -> list[ContentVariant]:
        await self.get_content(content_id, org_id)
        return await self._repo.list_variants(content_id)

    async def update_variant(
        self, content_id: UUID, variant_id: UUID, org_id: UUID, data: dict,
    ) -> ContentVariant:
        await self.get_content(content_id, org_id)
        variant = await self._repo.get_variant(variant_id)
        if not variant or variant.content_id != content_id:
            raise NotFoundError("Variant not found")
        update_data = {}
        for field in ("title", "body", "hashtags", "sort_order"):
            if field in data:
                update_data[field] = data[field]
        if "metadata" in data:
            update_data["metadata_"] = data["metadata"]
        return await self._repo.update_variant(variant, update_data)

    async def delete_variant(
        self, content_id: UUID, variant_id: UUID, org_id: UUID,
    ) -> None:
        await self.get_content(content_id, org_id)
        variant = await self._repo.get_variant(variant_id)
        if not variant or variant.content_id != content_id:
            raise NotFoundError("Variant not found")
        await self._repo.delete_variant(variant)

    async def attach_variant_media(
        self, content_id: UUID, variant_id: UUID, org_id: UUID, data: dict,
    ) -> VariantMedia:
        await self.get_content(content_id, org_id)
        variant = await self._repo.get_variant(variant_id)
        if not variant or variant.content_id != content_id:
            raise NotFoundError("Variant not found")
        vm = VariantMedia(
            variant_id=variant_id,
            media_asset_id=UUID(data["media_asset_id"]),
            organization_id=org_id,
            role=MediaRoleType(data.get("role", "SOURCE")),
            sort_order=data.get("sort_order", 0),
            metadata_=data.get("metadata"),
        )
        return await self._repo.add_variant_media(vm)

    async def detach_variant_media(
        self, content_id: UUID, variant_id: UUID, media_id: UUID, org_id: UUID,
    ) -> None:
        await self.get_content(content_id, org_id)
        vm = await self._repo.get_variant_media(media_id)
        if not vm or vm.variant_id != variant_id:
            raise NotFoundError("Variant media not found")
        await self._repo.remove_variant_media(vm)

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
