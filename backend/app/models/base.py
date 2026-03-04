import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def generate_uuid() -> uuid.UUID:
    """Generate a UUID v4 (v7 not natively supported; use v4 with time-sortable index)."""
    return uuid.uuid4()


class TimestampMixin:
    """created_at / updated_at columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SoftDeleteMixin:
    """Soft-delete via deleted_at column."""

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


__all__ = ["Base", "TimestampMixin", "SoftDeleteMixin", "generate_uuid"]
