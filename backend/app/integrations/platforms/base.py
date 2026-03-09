"""PlatformAdapter abstract base class — S4 (F12)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PublishResult:
    success: bool
    platform_post_id: str | None = None
    platform_url: str | None = None
    error_message: str | None = None


@dataclass
class ChannelInfo:
    platform_account_id: str
    name: str
    profile_url: str | None = None
    followers_count: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class TokenInfo:
    access_token: str
    refresh_token: str | None = None
    expires_in: int | None = None


@dataclass
class ContentValidationError:
    field: str
    message: str


@dataclass
class CommentData:
    """Single comment fetched from a platform."""

    external_id: str
    text: str
    author_name: str
    author_profile_url: str | None = None
    parent_external_id: str | None = None
    platform_created_at: datetime | None = None


@dataclass
class CommentActionResult:
    """Result of a comment action (reply / hide / delete)."""

    success: bool
    error_message: str | None = None


class PlatformAdapter(ABC):
    """Abstract base class for social media platform integrations."""

    @abstractmethod
    async def get_auth_url(self, redirect_uri: str, state: str) -> str:
        """Return OAuth authorization URL."""
        ...

    @abstractmethod
    async def exchange_code(self, code: str, redirect_uri: str) -> TokenInfo:
        """Exchange OAuth authorization code for tokens."""
        ...

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> TokenInfo:
        """Refresh an expired access token."""
        ...

    @abstractmethod
    async def get_channel_info(self, access_token: str) -> ChannelInfo:
        """Get channel/account information."""
        ...

    @abstractmethod
    async def publish(self, access_token: str, content: dict) -> PublishResult:
        """Publish content to the platform."""
        ...

    @abstractmethod
    async def validate_content(self, content: dict) -> list[ContentValidationError]:
        """Validate content against platform constraints."""
        ...

    @abstractmethod
    def get_rate_limit_config(self) -> dict:
        """Return rate limit configuration for this platform."""
        ...

    # ── Comment methods (Phase 1-B) ─────────────────────

    @abstractmethod
    async def get_comments(
        self,
        access_token: str,
        channel_id: str,
        since: datetime | None = None,
        page_token: str | None = None,
        max_results: int = 100,
    ) -> tuple[list[CommentData], str | None]:
        """Fetch comments from the platform.

        Returns (comments, next_page_token). next_page_token is None when exhausted.
        """
        ...

    @abstractmethod
    async def reply_to_comment(
        self, access_token: str, comment_external_id: str, text: str
    ) -> CommentActionResult:
        """Post a reply to a comment on the platform."""
        ...

    @abstractmethod
    async def hide_comment(
        self, access_token: str, comment_external_id: str
    ) -> CommentActionResult:
        """Hide (moderate) a comment on the platform."""
        ...

    @abstractmethod
    async def delete_comment(
        self, access_token: str, comment_external_id: str
    ) -> CommentActionResult:
        """Delete a comment on the platform."""
        ...
