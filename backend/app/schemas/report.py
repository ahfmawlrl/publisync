"""Pydantic schemas for Report endpoints — S18 (F19)."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class ReportGenerateRequest(BaseModel):
    period: str = Field(..., pattern="^(WEEKLY|MONTHLY|QUARTERLY)$")
    period_start: date
    period_end: date
    include_sections: list[str] | None = None


class ReportUpdateRequest(BaseModel):
    title: str | None = None
    content: dict | None = None


class ReportListItem(BaseModel):
    id: str
    title: str
    period: str
    period_start: date
    period_end: date
    status: str
    generated_by: str | None = None
    created_at: datetime
    finalized_at: datetime | None = None


class ReportResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    period: str
    period_start: date
    period_end: date
    status: str
    content: dict
    pdf_url: str | None = None
    generated_by: str | None = None
    created_by: str
    finalized_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
