"""Media Library ORM models (Phase 2, F11).

Tables: media_assets, media_folders, content_media_assets.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid
from app.models.enums import MediaType


class MediaFolder(Base, TimestampMixin):
    """Hierarchical folder structure for organizing media assets."""

    __tablename__ = "media_folders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_folders.id", ondelete="CASCADE"), nullable=True
    )

    # Self-referential relationship
    children: Mapped[list["MediaFolder"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )
    parent: Mapped["MediaFolder | None"] = relationship(
        back_populates="children", remote_side=[id]
    )
    assets: Mapped[list["MediaAsset"]] = relationship(back_populates="folder")

    __table_args__ = (
        Index("idx_media_folders_org_id", "organization_id"),
        Index("idx_media_folders_parent_id", "parent_id"),
        UniqueConstraint("organization_id", "parent_id", "name", name="uq_media_folder_name"),
    )


class MediaAsset(Base, TimestampMixin):
    """Individual media file metadata stored with MinIO object reference."""

    __tablename__ = "media_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    media_type: Mapped[MediaType] = mapped_column(Enum(MediaType), nullable=False)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # bytes
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)  # seconds (video/audio)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)  # pixels
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)  # pixels
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), default=list)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)
    folder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_folders.id", ondelete="SET NULL"), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    thumbnail_url: Mapped[str | None] = mapped_column(String(1024), nullable=True, default=None)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    folder: Mapped["MediaFolder | None"] = relationship(back_populates="assets")
    content_associations: Mapped[list["ContentMediaAsset"]] = relationship(
        back_populates="media_asset", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_media_assets_org_id", "organization_id"),
        Index("idx_media_assets_folder_id", "folder_id"),
        Index("idx_media_assets_media_type", "media_type"),
        Index("idx_media_assets_created_by", "created_by"),
        Index("idx_media_assets_tags", "tags", postgresql_using="gin"),
        Index("idx_media_assets_created_at", "created_at"),
    )


class ContentMediaAsset(Base, TimestampMixin):
    """Association table linking contents to media assets with ordering."""

    __tablename__ = "content_media_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contents.id", ondelete="CASCADE"), nullable=False
    )
    media_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    media_asset: Mapped["MediaAsset"] = relationship(back_populates="content_associations")

    __table_args__ = (
        UniqueConstraint("content_id", "media_asset_id", name="uq_content_media"),
        Index("idx_content_media_content_id", "content_id"),
        Index("idx_content_media_asset_id", "media_asset_id"),
        Index("idx_content_media_org_id", "organization_id"),
    )
