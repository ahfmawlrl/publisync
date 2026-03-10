"""Pydantic schemas for Approval endpoints — S6 (F09)."""

from pydantic import BaseModel


class ApprovalHistoryResponse(BaseModel):
    id: str
    request_id: str
    step: int
    action: str
    reviewer_id: str | None = None
    comment: str | None = None
    created_at: str


class ApprovalRequestResponse(BaseModel):
    id: str
    content_id: str
    organization_id: str
    workflow_id: str | None = None
    current_step: int
    status: str
    requested_by: str
    requested_by_name: str | None = None
    content_title: str | None = None
    platforms: list[str] = []
    is_urgent: bool = False
    comment: str | None = None
    histories: list[ApprovalHistoryResponse] = []
    created_at: str
    updated_at: str


class ApprovalActionRequest(BaseModel):
    comment: str | None = None


class WorkflowResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    steps: list[dict] | None = None
    is_active: bool = True
    created_at: str


class WorkflowUpdateRequest(BaseModel):
    name: str | None = None
    steps: list[dict] | None = None
    is_active: bool | None = None
