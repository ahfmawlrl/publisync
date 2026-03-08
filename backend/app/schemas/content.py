"""Pydantic schemas for Content endpoints — S5 (F01)."""

from pydantic import BaseModel


class ContentCreateRequest(BaseModel):
    title: str
    body: str | None = None
    platforms: list[str] = []
    channel_ids: list[str] = []
    scheduled_at: str | None = None
    platform_contents: dict | None = None
    media_urls: list[str] = []
    ai_generated: bool = False
    metadata: dict | None = None


class ContentUpdateRequest(BaseModel):
    title: str | None = None
    body: str | None = None
    platforms: list[str] | None = None
    channel_ids: list[str] | None = None
    scheduled_at: str | None = None
    platform_contents: dict | None = None
    media_urls: list[str] | None = None
    metadata: dict | None = None


class ContentResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    body: str | None = None
    status: str
    platforms: list[str] = []
    channel_ids: list[str] = []
    scheduled_at: str | None = None
    author_id: str
    author_name: str | None = None
    platform_contents: dict | None = None
    metadata: dict | None = None
    ai_generated: bool = False
    media_urls: list[str] = []
    created_at: str
    updated_at: str


class ContentVersionResponse(BaseModel):
    id: str
    content_id: str
    version: int
    title: str
    body: str | None = None
    metadata: dict | None = None
    changed_by: str
    created_at: str


class PublishResultResponse(BaseModel):
    id: str
    content_id: str
    channel_id: str
    status: str
    platform_post_id: str | None = None
    platform_url: str | None = None
    error_message: str | None = None
    retry_count: int = 0
    views: int = 0
    likes: int = 0
    shares: int = 0
    comments_count: int = 0
    created_at: str


class BulkActionRequest(BaseModel):
    content_ids: list[str]
    action: str  # "delete" | "archive" | "cancel_schedule"
