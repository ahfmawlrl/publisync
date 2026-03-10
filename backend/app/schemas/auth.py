"""Pydantic schemas for auth endpoints."""

from pydantic import BaseModel, EmailStr

# ── Login ─────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    status: str
    profile_image_url: str | None = None

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    tokens: TokenResponse
    user: UserResponse


# ── Refresh ───────────────────────────────────────────────

class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ── Password Reset ───────────────────────────────────────

class PasswordResetRequestBody(BaseModel):
    email: EmailStr


class PasswordResetBody(BaseModel):
    token: str
    new_password: str


# ── Invitation ───────────────────────────────────────────

class InviteAcceptRequest(BaseModel):
    token: str
    name: str
    password: str


class InviteVerifyResponse(BaseModel):
    email: str
    role: str
    organization_name: str
    expires_at: str
