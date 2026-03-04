"""Report ORM model — Phase 3 (F19 운영 리포트)."""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, generate_uuid
from app.models.enums import ReportPeriod, ReportStatus


class Report(Base, TimestampMixin):
    """AI-generated or manual operation report per organization."""

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=generate_uuid
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    period: Mapped[ReportPeriod] = mapped_column(Enum(ReportPeriod), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus), nullable=False, default=ReportStatus.GENERATING
    )
    content: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    pdf_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    generated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    finalized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("idx_reports_organization_id", "organization_id"),
        Index("idx_reports_period", "period"),
        Index("idx_reports_status", "status"),
        Index("idx_reports_created_at", "created_at"),
    )
