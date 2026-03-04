"""Pydantic schemas for Dashboard endpoints — S7."""

from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    total_contents: int = 0
    published_contents: int = 0
    scheduled_contents: int = 0
    pending_approvals: int = 0
    active_channels: int = 0
    total_views: int = 0
    total_likes: int = 0


class PlatformTrendItem(BaseModel):
    platform: str
    published: int = 0
    views: int = 0
    likes: int = 0
    shares: int = 0


class ApprovalStatusItem(BaseModel):
    status: str
    count: int = 0


class RecentContentItem(BaseModel):
    id: str
    title: str
    status: str
    platforms: list[str] = []
    created_at: str
    author_id: str


class TodayScheduleItem(BaseModel):
    id: str
    title: str
    scheduled_at: str
    platforms: list[str] = []
    status: str


class OrgSummaryItem(BaseModel):
    id: str
    name: str
    slug: str
    total_contents: int = 0
    published_contents: int = 0
    active_channels: int = 0
    pending_approvals: int = 0


class SearchResultItem(BaseModel):
    id: str
    type: str  # "content"
    title: str
    snippet: str | None = None
    status: str
    created_at: str


class AnnouncementResponse(BaseModel):
    id: str
    title: str
    content: str
    type: str
    is_active: bool
    publish_at: str | None = None
    created_by: str | None = None
    created_at: str


class AnnouncementCreateRequest(BaseModel):
    title: str
    content: str
    type: str = "INFO"
    is_active: bool = True
    publish_at: str | None = None


# ── Phase 1-B additions ─────────────────────────────────


class SentimentSummaryItem(BaseModel):
    sentiment: str  # POSITIVE, NEUTRAL, NEGATIVE, DANGEROUS
    count: int = 0
    percentage: float = 0.0


class RateLimitStatusItem(BaseModel):
    platform: str
    quota_limit: int = 0
    quota_used: int = 0
    remaining: int = 0
    reset_at: str | None = None
