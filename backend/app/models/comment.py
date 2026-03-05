"""Comment and ReplyTemplate ORM models (Phase 1-B)."""

import uuid

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin, generate_uuid
from app.models.enums import CommentSentiment, CommentStatus, PlatformType


class Comment(Base, TimestampMixin):
    """Platform comments collected by Celery Beat (5min interval)."""

    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    content_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contents.id"), nullable=True
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("channels.id"), nullable=False
    )
    platform: Mapped[PlatformType] = mapped_column(nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Comment content
    text: Mapped[str] = mapped_column(Text, nullable=False)
    author_name: Mapped[str] = mapped_column(String(200), nullable=False)
    author_profile_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    parent_comment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("comments.id"), nullable=True
    )

    # Sentiment analysis
    sentiment: Mapped[CommentSentiment | None] = mapped_column(nullable=True)
    sentiment_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    dangerous_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    keywords: Mapped[list[str] | None] = mapped_column(ARRAY(String(100)), nullable=True)

    # Status & reply
    status: Mapped[CommentStatus] = mapped_column(default=CommentStatus.UNPROCESSED, nullable=False)
    reply_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    reply_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    replied_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hidden_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    delete_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    platform_created_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    replies = relationship("Comment", backref="parent", remote_side="Comment.id", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("channel_id", "external_id", name="uq_comments_channel_external"),
        Index("idx_comments_org_id", "organization_id"),
        Index("idx_comments_content_id", "content_id"),
        Index("idx_comments_channel_id", "channel_id"),
        Index("idx_comments_sentiment", "sentiment"),
        Index("idx_comments_status", "status"),
        Index("idx_comments_created_at", "created_at"),
        Index("idx_comments_dangerous", "sentiment", postgresql_where=func.cast("sentiment", String) == "DANGEROUS"),
    )


class ReplyTemplate(Base, TimestampMixin, SoftDeleteMixin):
    """Reusable reply templates for comments."""

    __tablename__ = "reply_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[list[str] | None] = mapped_column(ARRAY(String(100)), nullable=True)
    usage_count: Mapped[int] = mapped_column(default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    __table_args__ = (
        Index("idx_templates_org_id", "organization_id"),
        Index("idx_templates_category", "category"),
        Index("idx_templates_is_active", "is_active"),
    )
