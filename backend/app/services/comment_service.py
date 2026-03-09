"""Comment and ReplyTemplate business logic — S9 (F04)."""

from datetime import UTC, datetime
from uuid import UUID

import structlog

from app.core.encryption import decrypt_token
from app.core.exceptions import NotFoundError, ValidationError, WorkflowStateConflictError
from app.integrations.platforms import get_adapter
from app.models.comment import Comment, ReplyTemplate
from app.models.enums import CommentSentiment, CommentStatus
from app.repositories.channel_repository import ChannelRepository
from app.repositories.comment_repository import CommentRepository

logger = structlog.get_logger()


def _index_comment_to_search(comment: Comment) -> None:
    """Index/update a comment in Meilisearch (best-effort)."""
    try:
        from app.integrations.search import index_document

        doc = {
            "id": str(comment.id),
            "organization_id": str(comment.organization_id),
            "text": comment.text or "",
            "author_name": comment.author_name or "",
            "platform": comment.platform.value if hasattr(comment.platform, "value") else str(comment.platform),
            "sentiment": comment.sentiment.value if comment.sentiment and hasattr(comment.sentiment, "value") else None,
            "status": comment.status.value if hasattr(comment.status, "value") else str(comment.status),
            "created_at": comment.created_at.isoformat() if comment.created_at else "",
        }
        index_document("comments", doc)
    except Exception as exc:
        logger.warning("search_index_comment_failed", error=str(exc))


class CommentNotFoundError(NotFoundError):
    detail = "Comment not found"


class ReplyTemplateNotFoundError(NotFoundError):
    detail = "Reply template not found"


# Valid status transitions for comments
_VALID_TRANSITIONS: dict[CommentStatus, set[CommentStatus]] = {
    CommentStatus.UNPROCESSED: {
        CommentStatus.PUBLISHED,
        CommentStatus.HIDDEN,
        CommentStatus.PENDING_DELETE,
    },
    CommentStatus.PUBLISHED: {
        CommentStatus.HIDDEN,
        CommentStatus.PENDING_DELETE,
    },
    CommentStatus.HIDDEN: {
        CommentStatus.UNPROCESSED,
        CommentStatus.PENDING_DELETE,
    },
    CommentStatus.PENDING_DELETE: {
        CommentStatus.DELETED,
        CommentStatus.UNPROCESSED,
    },
    CommentStatus.DELETED: set(),
}


class CommentService:
    def __init__(self, repo: CommentRepository, channel_repo: ChannelRepository | None = None) -> None:
        self._repo = repo
        self._channel_repo = channel_repo

    def _validate_transition(self, current: CommentStatus, target: CommentStatus) -> None:
        if target not in _VALID_TRANSITIONS.get(current, set()):
            raise WorkflowStateConflictError(
                f"Cannot transition comment from {current.value} to {target.value}"
            )

    # ── Comment queries ──────────────────────────────────

    async def list_comments(
        self,
        org_id: UUID,
        page: int = 1,
        limit: int = 20,
        status: str | None = None,
        platform: str | None = None,
        channel_id: UUID | None = None,
        search: str | None = None,
    ) -> tuple[list[Comment], int]:
        offset = (page - 1) * limit
        return await self._repo.list_comments(
            org_id,
            offset=offset,
            limit=limit,
            status=status,
            platform=platform,
            channel_id=channel_id,
            search=search,
        )

    async def get_comment(self, comment_id: UUID, org_id: UUID) -> Comment:
        comment = await self._repo.get_comment(comment_id)
        if comment is None or comment.organization_id != org_id:
            raise CommentNotFoundError()
        return comment

    async def get_dangerous_comments(
        self,
        org_id: UUID,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Comment], int]:
        offset = (page - 1) * limit
        return await self._repo.get_dangerous_comments(org_id, offset=offset, limit=limit)

    # ── Platform adapter helper ────────────────────────

    async def _get_platform_context(self, comment: Comment) -> tuple:
        """Get (adapter, access_token) for a comment's channel. Returns (None, None) if unavailable."""
        if self._channel_repo is None:
            return None, None
        channel = await self._channel_repo.get_by_id(comment.channel_id)
        if channel is None or channel.access_token_enc is None:
            return None, None
        try:
            access_token = decrypt_token(channel.access_token_enc)
            adapter = get_adapter(channel.platform)
            return adapter, access_token
        except Exception:
            logger.warning("platform_context_failed", channel_id=str(comment.channel_id))
            return None, None

    # ── Comment actions ──────────────────────────────────

    async def reply_comment(
        self, comment_id: UUID, org_id: UUID, actor_id: UUID, text: str
    ) -> Comment:
        comment = await self.get_comment(comment_id, org_id)

        if comment.status == CommentStatus.DELETED:
            raise WorkflowStateConflictError("Cannot reply to a deleted comment")

        # Try platform action (best-effort: DB state changes regardless)
        adapter, access_token = await self._get_platform_context(comment)
        platform_error = None
        if adapter and access_token:
            result = await adapter.reply_to_comment(access_token, comment.external_id, text)
            if not result.success:
                platform_error = result.error_message
                logger.warning(
                    "platform_reply_failed",
                    comment_id=str(comment_id),
                    error=platform_error,
                )

        now = datetime.now(UTC)
        comment = await self._repo.update_comment(comment, {
            "reply_text": text,
            "replied_at": now,
            "status": CommentStatus.PUBLISHED,
            "processed_by": actor_id,
        })
        logger.info("comment_replied", comment_id=str(comment_id), actor_id=str(actor_id))
        _index_comment_to_search(comment)
        return comment

    async def hide_comment(
        self, comment_id: UUID, org_id: UUID, actor_id: UUID, reason: str | None = None
    ) -> Comment:
        comment = await self.get_comment(comment_id, org_id)
        self._validate_transition(comment.status, CommentStatus.HIDDEN)

        # Try platform action (best-effort)
        adapter, access_token = await self._get_platform_context(comment)
        if adapter and access_token:
            result = await adapter.hide_comment(access_token, comment.external_id)
            if not result.success:
                logger.warning(
                    "platform_hide_failed",
                    comment_id=str(comment_id),
                    error=result.error_message,
                )

        comment = await self._repo.update_comment(comment, {
            "status": CommentStatus.HIDDEN,
            "hidden_reason": reason,
            "processed_by": actor_id,
        })
        logger.info("comment_hidden", comment_id=str(comment_id), actor_id=str(actor_id))
        return comment

    async def request_delete(
        self, comment_id: UUID, org_id: UUID, actor_id: UUID, reason: str | None = None
    ) -> Comment:
        comment = await self.get_comment(comment_id, org_id)
        self._validate_transition(comment.status, CommentStatus.PENDING_DELETE)

        comment = await self._repo.update_comment(comment, {
            "status": CommentStatus.PENDING_DELETE,
            "delete_reason": reason,
            "processed_by": actor_id,
        })
        logger.info("comment_delete_requested", comment_id=str(comment_id), actor_id=str(actor_id))
        return comment

    async def ignore_dangerous(
        self, comment_id: UUID, org_id: UUID, actor_id: UUID
    ) -> Comment:
        comment = await self.get_comment(comment_id, org_id)

        if comment.sentiment != CommentSentiment.DANGEROUS:
            raise ValidationError("Comment is not marked as dangerous")

        comment = await self._repo.update_comment(comment, {
            "sentiment": CommentSentiment.NEUTRAL,
            "dangerous_level": None,
            "processed_by": actor_id,
        })
        logger.info("comment_danger_ignored", comment_id=str(comment_id), actor_id=str(actor_id))
        return comment

    async def approve_delete(
        self, comment_id: UUID, org_id: UUID, actor_id: UUID
    ) -> Comment:
        comment = await self.get_comment(comment_id, org_id)
        self._validate_transition(comment.status, CommentStatus.DELETED)

        # Try platform action (best-effort)
        adapter, access_token = await self._get_platform_context(comment)
        if adapter and access_token:
            result = await adapter.delete_comment(access_token, comment.external_id)
            if not result.success:
                logger.warning(
                    "platform_delete_failed",
                    comment_id=str(comment_id),
                    error=result.error_message,
                )

        comment = await self._repo.update_comment(comment, {
            "status": CommentStatus.DELETED,
            "processed_by": actor_id,
        })
        logger.info("comment_delete_approved", comment_id=str(comment_id), actor_id=str(actor_id))
        return comment

    # ── ReplyTemplate CRUD ───────────────────────────────

    async def list_templates(
        self, org_id: UUID, category: str | None = None
    ) -> list[ReplyTemplate]:
        return await self._repo.list_templates(org_id, category=category)

    async def get_template(self, template_id: UUID, org_id: UUID) -> ReplyTemplate:
        template = await self._repo.get_template(template_id)
        if template is None or template.organization_id != org_id:
            raise ReplyTemplateNotFoundError()
        return template

    async def create_template(
        self, org_id: UUID, actor_id: UUID, data: dict
    ) -> ReplyTemplate:
        template = ReplyTemplate(
            organization_id=org_id,
            category=data["category"],
            name=data["name"],
            content=data["content"],
            variables=data.get("variables"),
            created_by=actor_id,
        )
        template = await self._repo.create_template(template)
        logger.info("reply_template_created", template_id=str(template.id))
        return template

    async def update_template(
        self, template_id: UUID, org_id: UUID, data: dict
    ) -> ReplyTemplate:
        template = await self.get_template(template_id, org_id)

        update_data: dict = {}
        if data.get("category") is not None:
            update_data["category"] = data["category"]
        if data.get("name") is not None:
            update_data["name"] = data["name"]
        if data.get("content") is not None:
            update_data["content"] = data["content"]
        if "variables" in data:
            update_data["variables"] = data["variables"]
        if data.get("is_active") is not None:
            update_data["is_active"] = data["is_active"]

        if update_data:
            template = await self._repo.update_template(template, update_data)

        logger.info("reply_template_updated", template_id=str(template_id))
        return template

    async def delete_template(self, template_id: UUID, org_id: UUID) -> None:
        template = await self.get_template(template_id, org_id)
        await self._repo.soft_delete_template(template)
        logger.info("reply_template_deleted", template_id=str(template_id))
