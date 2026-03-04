"""Pydantic schemas for User endpoints."""

from pydantic import BaseModel, EmailStr

from app.models.enums import UserRole, UserStatus


# ── Request ──────────────────────────────────────────────

class UserCreateRequest(BaseModel):
    email: EmailStr
    name: str
    role: UserRole
    organization_id: str
    password: str | None = None  # None → send invite instead


class UserUpdateRequest(BaseModel):
    name: str | None = None
    role: UserRole | None = None
    status: UserStatus | None = None
    profile_image_url: str | None = None


# ── Response ─────────────────────────────────────────────

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    status: str
    organization_id: str | None = None
    profile_image_url: str | None = None
    last_login_at: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


class RoleResponse(BaseModel):
    id: str
    name: str
    permissions: list[str]
    description: str | None = None

    model_config = {"from_attributes": True}


class UserMeResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    status: str
    profile_image_url: str | None = None
    organizations: list["UserOrgBrief"]

    model_config = {"from_attributes": True}


class UserOrgBrief(BaseModel):
    id: str
    name: str
    slug: str
    role: str
    is_primary: bool
