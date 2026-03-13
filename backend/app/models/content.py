"""Content, ContentVersion, PublishResult, ContentVariant, VariantMedia — S5 (F01)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.media import MediaAsset
    from app.models.user import User

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid
from app.models.enums import ContentStatus, MediaRoleType, PlatformType, PublishResultStatus


class Content(Base, TimestampMixin):
    __tablename__ = "contents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus), nullable=False, default=ContentStatus.DRAFT
    )
    platforms: Mapped[list[str] | None] = mapped_column(ARRAY(String), default=list)
    channel_ids: Mapped[list[str] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), default=list)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    platform_contents: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    media_urls: Mapped[list[str] | None] = mapped_column(ARRAY(String), default=list)
    source_media_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True
    )
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    author: Mapped[User] = relationship(foreign_keys=[author_id], lazy="noload")
    source_media: Mapped[MediaAsset | None] = relationship(foreign_keys=[source_media_id], lazy="noload")
    versions: Mapped[list[ContentVersion]] = relationship(back_populates="content", cascade="all, delete-orphan")
    publish_results: Mapped[list[PublishResult]] = relationship(
        back_populates="content", cascade="all, delete-orphan",
    )
    variants: Mapped[list[ContentVariant]] = relationship(
        back_populates="content", cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_contents_org_id", "organization_id"),
        Index("idx_contents_status", "status"),
        Index("idx_contents_author_id", "author_id"),
        Index("idx_contents_scheduled_at", "scheduled_at"),
        Index("idx_contents_search_vector", "search_vector", postgresql_using="gin"),
    )


class ContentVersion(Base, TimestampMixin):
    __tablename__ = "content_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contents.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)
    changed_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    content: Mapped[Content] = relationship(back_populates="versions")

    __table_args__ = (
        Index("idx_content_versions_content_id", "content_id"),
        Index("idx_content_versions_org_id", "organization_id"),
    )


class PublishResult(Base, TimestampMixin):
    __tablename__ = "publish_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contents.id", ondelete="CASCADE"), nullable=False
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_variants.id", ondelete="SET NULL"), nullable=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("channels.id"), nullable=False
    )
    status: Mapped[PublishResultStatus] = mapped_column(
        Enum(PublishResultStatus), nullable=False, default=PublishResultStatus.PENDING
    )
    platform_post_id: Mapped[str | None] = mapped_column(String(255))
    platform_url: Mapped[str | None] = mapped_column(String(2048))
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)

    content: Mapped[Content] = relationship(back_populates="publish_results")
    variant: Mapped[ContentVariant | None] = relationship(lazy="noload")

    __table_args__ = (
        Index("idx_publish_results_content_id", "content_id"),
        Index("idx_publish_results_org_id", "organization_id"),
        Index("idx_publish_results_channel_id", "channel_id"),
        Index("idx_publish_results_status", "status"),
        Index("idx_publish_results_variant_id", "variant_id"),
    )


class ContentVariant(Base, TimestampMixin):
    """Platform-specific content derivative (v2.0)."""

    __tablename__ = "content_variants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contents.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    platform: Mapped[PlatformType] = mapped_column(Enum(PlatformType), nullable=False)
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("channels.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str | None] = mapped_column(String(500))
    body: Mapped[str | None] = mapped_column(Text)
    hashtags: Mapped[list[str] | None] = mapped_column(ARRAY(String), default=list)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    content: Mapped[Content] = relationship(back_populates="variants")
    media: Mapped[list[VariantMedia]] = relationship(
        back_populates="variant", cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("content_id", "platform", "channel_id", name="uq_variant_content_platform_channel"),
        Index("idx_content_variants_content_id", "content_id"),
        Index("idx_content_variants_org_id", "organization_id"),
        Index("idx_content_variants_platform", "platform"),
        Index("idx_content_variants_channel_id", "channel_id"),
    )


class VariantMedia(Base, TimestampMixin):
    """Association between ContentVariant and MediaAsset with role (v2.0)."""

    __tablename__ = "variant_media"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_variants.id", ondelete="CASCADE"), nullable=False
    )
    media_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    role: Mapped[MediaRoleType] = mapped_column(
        Enum(MediaRoleType), nullable=False, default=MediaRoleType.SOURCE
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)

    variant: Mapped[ContentVariant] = relationship(back_populates="media")
    media_asset: Mapped[MediaAsset] = relationship(lazy="noload")

    __table_args__ = (
        UniqueConstraint("variant_id", "media_asset_id", "role", name="uq_variant_media_role"),
        Index("idx_variant_media_variant_id", "variant_id"),
        Index("idx_variant_media_media_id", "media_asset_id"),
        Index("idx_variant_media_org_id", "organization_id"),
        Index("idx_variant_media_role", "role"),
    )
