"""AuditLog ORM model (Phase 1-B). INSERT-ONLY with monthly partitioning."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import generate_uuid
from app.models.enums import AuditAction, UserRole


class AuditLog(Base):
    """Immutable audit trail. INSERT-ONLY — no UPDATE/DELETE allowed.

    In production, this table uses RANGE partitioning on created_at (monthly).
    The migration creates the parent table; partition management is handled
    by a Celery Beat task (monthly).
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    actor_role: Mapped[UserRole | None] = mapped_column(nullable=True)
    action: Mapped[AuditAction] = mapped_column(nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    changes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    request_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    actor: Mapped[User] = relationship(foreign_keys=[actor_id], lazy="noload")

    __table_args__ = (
        Index("idx_audit_logs_org_id", "organization_id"),
        Index("idx_audit_logs_actor_id", "actor_id"),
        Index("idx_audit_logs_action", "action"),
        Index("idx_audit_logs_resource_type", "resource_type"),
        Index("idx_audit_logs_created_at", "created_at"),
        Index("idx_audit_logs_org_action_created", "organization_id", "action", "created_at"),
    )
