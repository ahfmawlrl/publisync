"""AI Usage Log + AI Job ORM models.

AiUsageLog (Phase 1-B) — Tracks token consumption and cost.
AiJob (Phase 2) — Tracks async AI job status (subtitles, shortform).
"""

import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import generate_uuid
from app.models.enums import AiJobStatus, AiJobType, AiTaskType


class AiUsageLog(Base):
    """Per-request AI usage tracking for cost management and monitoring."""

    __tablename__ = "ai_usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    task_type: Mapped[AiTaskType] = mapped_column(nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=0, nullable=False)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    output_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_fallback: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_ai_usage_org_id", "organization_id"),
        Index("idx_ai_usage_user_id", "user_id"),
        Index("idx_ai_usage_task_type", "task_type"),
        Index("idx_ai_usage_model", "model"),
        Index("idx_ai_usage_created_at", "created_at"),
        Index("idx_ai_usage_org_month", "organization_id", "created_at"),
    )


class AiJob(Base):
    """Async AI job tracking (Phase 2 — subtitles, shortform extraction).

    Pattern: 202 Accepted → jobId → polling GET /ai/jobs/:jobId.
    """

    __tablename__ = "ai_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    job_type: Mapped[AiJobType] = mapped_column(Enum(AiJobType), nullable=False)
    status: Mapped[AiJobStatus] = mapped_column(
        Enum(AiJobStatus), nullable=False, default=AiJobStatus.PENDING
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0-100
    input_params: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True
    )
    started_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_ai_jobs_org_id", "organization_id"),
        Index("idx_ai_jobs_user_id", "user_id"),
        Index("idx_ai_jobs_status", "status"),
        Index("idx_ai_jobs_job_type", "job_type"),
        Index("idx_ai_jobs_created_at", "created_at"),
    )
