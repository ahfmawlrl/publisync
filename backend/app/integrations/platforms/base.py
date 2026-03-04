"""PlatformAdapter abstract base class — S4 (F12)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


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
