"""Stub adapters for Instagram, Facebook, X, Naver Blog — S4 scaffolding."""

from app.integrations.platforms.base import (
    ChannelInfo,
    ContentValidationError,
    PlatformAdapter,
    PublishResult,
    TokenInfo,
)


class StubAdapter(PlatformAdapter):
    """Stub adapter — returns placeholder responses for unimplemented platforms."""

    def __init__(self, platform_name: str) -> None:
        self._platform = platform_name

    async def get_auth_url(self, redirect_uri: str, state: str) -> str:
        raise NotImplementedError(f"{self._platform} OAuth is not yet implemented")

    async def exchange_code(self, code: str, redirect_uri: str) -> TokenInfo:
        raise NotImplementedError(f"{self._platform} OAuth is not yet implemented")

    async def refresh_token(self, refresh_token: str) -> TokenInfo:
        raise NotImplementedError(f"{self._platform} token refresh is not yet implemented")

    async def get_channel_info(self, access_token: str) -> ChannelInfo:
        raise NotImplementedError(f"{self._platform} channel info is not yet implemented")

    async def publish(self, access_token: str, content: dict) -> PublishResult:
        return PublishResult(success=False, error_message=f"{self._platform} publish not yet implemented")

    async def validate_content(self, content: dict) -> list[ContentValidationError]:
        return []

    def get_rate_limit_config(self) -> dict:
        return {"requests_per_hour": 200, "window": "1h"}
