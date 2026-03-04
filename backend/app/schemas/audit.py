"""Pydantic schemas for Audit Log endpoints — S12 (F14)."""

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: str
    organization_id: str
    actor_id: str | None = None
    actor_role: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    changes: dict | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None
    created_at: str


class AuditLogExportRequest(BaseModel):
    format: str = "csv"  # "csv" or "pdf"
    start_date: str
    end_date: str
    actions: list[str] | None = None
