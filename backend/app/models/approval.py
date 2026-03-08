"""ApprovalWorkflow, ApprovalRequest, ApprovalHistory — S6 (F09)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.content import Content
    from app.models.user import User

from sqlalchemy import Boolean, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid
from app.models.enums import ApprovalAction, ApprovalStatus


class ApprovalWorkflow(Base, TimestampMixin):
    __tablename__ = "approval_workflows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    steps: Mapped[dict | None] = mapped_column(JSONB, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    requests: Mapped[list[ApprovalRequest]] = relationship(back_populates="workflow")

    __table_args__ = (
        Index("idx_approval_workflows_org_id", "organization_id"),
    )


class ApprovalRequest(Base, TimestampMixin):
    __tablename__ = "approval_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contents.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("approval_workflows.id")
    )
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING_REVIEW
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    is_urgent: Mapped[bool] = mapped_column(Boolean, default=False)
    comment: Mapped[str | None] = mapped_column(Text)

    requester: Mapped[User] = relationship(foreign_keys=[requested_by], lazy="noload")
    content: Mapped[Content] = relationship(foreign_keys=[content_id], lazy="noload")
    workflow: Mapped[ApprovalWorkflow | None] = relationship(back_populates="requests")
    histories: Mapped[list[ApprovalHistory]] = relationship(back_populates="request", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_approval_requests_org_id", "organization_id"),
        Index("idx_approval_requests_content_id", "content_id"),
        Index("idx_approval_requests_status", "status"),
    )


class ApprovalHistory(Base, TimestampMixin):
    __tablename__ = "approval_histories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("approval_requests.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    step: Mapped[int] = mapped_column(Integer, default=0)
    action: Mapped[ApprovalAction] = mapped_column(Enum(ApprovalAction), nullable=False)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    comment: Mapped[str | None] = mapped_column(Text)

    request: Mapped[ApprovalRequest] = relationship(back_populates="histories")

    __table_args__ = (
        Index("idx_approval_histories_request_id", "request_id"),
        Index("idx_approval_histories_org_id", "organization_id"),
    )
