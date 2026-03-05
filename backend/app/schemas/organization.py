"""Pydantic schemas for Organization and Agency endpoints."""

from pydantic import BaseModel

from app.models.enums import OrgPlan, OrgStatus

# ── Organization ─────────────────────────────────────────

class OrgCreateRequest(BaseModel):
    name: str
    slug: str
    plan: OrgPlan = OrgPlan.BASIC
    contact_email: str | None = None
    contact_phone: str | None = None
    agency_id: str | None = None


class OrgUpdateRequest(BaseModel):
    name: str | None = None
    status: OrgStatus | None = None
    plan: OrgPlan | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    logo_url: str | None = None
    settings: dict | None = None


class OrgResponse(BaseModel):
    id: str
    name: str
    slug: str
    status: str
    plan: str
    logo_url: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    storage_used_bytes: int
    storage_quota_bytes: int
    agency_id: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    slug: str
    role: str
    is_primary: bool


# ── Agency ───────────────────────────────────────────────

class AgencyCreateRequest(BaseModel):
    name: str
    contact_email: str | None = None
    contact_phone: str | None = None


class AgencyResponse(BaseModel):
    id: str
    name: str
    contact_email: str | None = None
    contact_phone: str | None = None
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}


# ── Badge Counts ─────────────────────────────────────────

class BadgeCountsResponse(BaseModel):
    pending_approvals: int = 0
    scheduled_posts: int = 0
    unread_comments: int = 0
    unread_notifications: int = 0
