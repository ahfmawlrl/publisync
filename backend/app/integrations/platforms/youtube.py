"""YouTube Data API v3 adapter — S4 (F12)."""

import structlog

from app.integrations.platforms.base import (
    ChannelInfo,
    ContentValidationError,
    PlatformAdapter,
    PublishResult,
    TokenInfo,
)

logger = structlog.get_logger()

YOUTUBE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
YOUTUBE_TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
YOUTUBE_SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"


class YouTubeAdapter(PlatformAdapter):
    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

    async def get_auth_url(self, redirect_uri: str, state: str) -> str:
        params = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": YOUTUBE_SCOPES,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{YOUTUBE_AUTH_URL}?{qs}"

    async def exchange_code(self, code: str, redirect_uri: str) -> TokenInfo:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(YOUTUBE_TOKEN_URL, data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            })
            resp.raise_for_status()
            data = resp.json()
        return TokenInfo(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_in=data.get("expires_in", 3600),
        )

    async def refresh_token(self, refresh_token: str) -> TokenInfo:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(YOUTUBE_TOKEN_URL, data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            })
            resp.raise_for_status()
            data = resp.json()
        return TokenInfo(
            access_token=data["access_token"],
            refresh_token=refresh_token,
            expires_in=data.get("expires_in", 3600),
        )

    async def get_channel_info(self, access_token: str) -> ChannelInfo:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{YOUTUBE_API_BASE}/channels",
                params={"part": "snippet,statistics", "mine": "true"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])

        if not items:
            raise ValueError("No YouTube channel found")

        ch = items[0]
        snippet = ch.get("snippet", {})
        stats = ch.get("statistics", {})
        return ChannelInfo(
            platform_account_id=ch["id"],
            name=snippet.get("title", ""),
            profile_url=f"https://youtube.com/channel/{ch['id']}",
            followers_count=int(stats.get("subscriberCount", 0)),
            metadata={"description": snippet.get("description", "")},
        )

    async def publish(self, access_token: str, content: dict) -> PublishResult:
        # Full implementation requires multipart upload — stub for S4
        logger.info("youtube_publish_stub", title=content.get("title"))
        return PublishResult(success=False, error_message="YouTube publish requires video upload (Phase S5)")

    async def validate_content(self, content: dict) -> list[ContentValidationError]:
        errors = []
        title = content.get("title", "")
        if len(title) > 100:
            errors.append(ContentValidationError("title", "YouTube 제목은 100자를 초과할 수 없습니다"))
        desc = content.get("body", "")
        if len(desc) > 5000:
            errors.append(ContentValidationError("body", "YouTube 설명은 5000자를 초과할 수 없습니다"))
        return errors

    def get_rate_limit_config(self) -> dict:
        return {"daily_quota_units": 10000, "window": "24h"}
