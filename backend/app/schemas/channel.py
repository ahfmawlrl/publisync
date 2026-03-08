"""Pydantic schemas for Channel endpoints — S4 (F12)."""

from pydantic import BaseModel

from app.models.enums import PlatformType


class ChannelResponse(BaseModel):
    id: str
    organization_id: str
    platform: str
    platform_account_id: str
    name: str
    status: str
    token_expires_at: str | None = None
    metadata: dict | None = None
    created_at: str

    model_config = {"from_attributes": True}


class ChannelConnectInitiateRequest(BaseModel):
    platform: PlatformType
    redirect_uri: str


class ChannelConnectInitiateResponse(BaseModel):
    auth_url: str
    state: str


class ChannelConnectCallbackRequest(BaseModel):
    platform: PlatformType
    code: str
    state: str
    redirect_uri: str


class ChannelHistoryResponse(BaseModel):
    id: str
    channel_id: str
    event_type: str
    details: dict | None = None
    actor_id: str | None = None
    actor_name: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


class ApiStatusResponse(BaseModel):
    platform: str
    requests_used: int = 0
    requests_limit: int = 0
    window: str = ""
    percentage_used: float = 0.0
