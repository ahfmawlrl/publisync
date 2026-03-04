"""Pydantic schemas for Comment and ReplyTemplate endpoints — S9 (F04)."""

from pydantic import BaseModel


class CommentResponse(BaseModel):
    id: str
    organization_id: str
    content_id: str | None = None
    channel_id: str
    platform: str
    external_id: str
    text: str
    author_name: str
    author_profile_url: str | None = None
    parent_comment_id: str | None = None
    sentiment: str | None = None
    sentiment_confidence: float | None = None
    dangerous_level: str | None = None
    keywords: list[str] | None = None
    status: str
    reply_text: str | None = None
    reply_draft: str | None = None
    replied_at: str | None = None
    hidden_reason: str | None = None
    delete_reason: str | None = None
    processed_by: str | None = None
    platform_created_at: str | None = None
    created_at: str
    updated_at: str


class DangerousCommentResponse(CommentResponse):
    """Extends CommentResponse — semantically marks dangerous comments."""

    pass


class CommentReplyRequest(BaseModel):
    text: str


class CommentHideRequest(BaseModel):
    reason: str | None = None


class CommentDeleteRequest(BaseModel):
    reason: str | None = None


# ── Reply Templates ──────────────────────────────────────


class ReplyTemplateResponse(BaseModel):
    id: str
    organization_id: str
    category: str
    name: str
    content: str
    variables: list[str] | None = None
    usage_count: int = 0
    is_active: bool = True
    created_by: str
    created_at: str
    updated_at: str


class ReplyTemplateCreateRequest(BaseModel):
    category: str
    name: str
    content: str
    variables: list[str] | None = None


class ReplyTemplateUpdateRequest(BaseModel):
    category: str | None = None
    name: str | None = None
    content: str | None = None
    variables: list[str] | None = None
    is_active: bool | None = None
