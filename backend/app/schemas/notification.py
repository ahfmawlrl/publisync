"""Pydantic schemas for Notification endpoints — S10 (F13/F07)."""

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    organization_id: str
    user_id: str
    type: str
    channel: str
    title: str
    message: str
    payload: dict | None = None
    is_read: bool
    read_at: str | None = None
    action_url: str | None = None
    created_at: str


class NotificationSettingResponse(BaseModel):
    id: str | None = None
    organization_id: str
    user_id: str
    channels: dict
    push_subscription: dict | None = None
    telegram_chat_id: str | None = None


class NotificationSettingUpdateRequest(BaseModel):
    channels: dict | None = None
    telegram_chat_id: str | None = None
    push_subscription: dict | None = None


class UnreadCountResponse(BaseModel):
    count: int


class TelegramTestRequest(BaseModel):
    chat_id: str


class TelegramChannelConfigRequest(BaseModel):
    """Configure Telegram notification channels for an organization."""
    enabled: bool = True
    chat_id: str
