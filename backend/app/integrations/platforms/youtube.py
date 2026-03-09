"""YouTube Data API v3 adapter — S4 (F12), S9 comments (Phase 1-B)."""

from datetime import datetime

import structlog

from app.integrations.platforms.base import (
    ChannelInfo,
    CommentActionResult,
    CommentData,
    ContentValidationError,
    PlatformAdapter,
    PublishResult,
    TokenInfo,
)

logger = structlog.get_logger()

YOUTUBE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
YOUTUBE_TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
YOUTUBE_SCOPES = (
    "https://www.googleapis.com/auth/youtube.upload "
    "https://www.googleapis.com/auth/youtube.readonly "
    "https://www.googleapis.com/auth/youtube.force-ssl"
)


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

    # ── Comment methods ──────────────────────────────────

    async def get_comments(
        self,
        access_token: str,
        channel_id: str,
        since: datetime | None = None,
        page_token: str | None = None,
        max_results: int = 100,
    ) -> tuple[list[CommentData], str | None]:
        """Fetch comment threads related to the channel."""
        import httpx

        params: dict = {
            "part": "snippet",
            "allThreadsRelatedToChannelId": channel_id,
            "maxResults": min(max_results, 100),
            "order": "time",
            "textFormat": "plainText",
        }
        if page_token:
            params["pageToken"] = page_token

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{YOUTUBE_API_BASE}/commentThreads",
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()

        comments: list[CommentData] = []
        for item in data.get("items", []):
            snippet = item["snippet"]["topLevelComment"]["snippet"]
            published_at = snippet.get("publishedAt")
            created_at = (
                datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                if published_at
                else None
            )

            # Skip comments older than `since`
            if since and created_at and created_at <= since:
                continue

            comments.append(CommentData(
                external_id=item["snippet"]["topLevelComment"]["id"],
                text=snippet.get("textDisplay", ""),
                author_name=snippet.get("authorDisplayName", ""),
                author_profile_url=snippet.get("authorProfileImageUrl"),
                parent_external_id=None,
                platform_created_at=created_at,
            ))

        next_page = data.get("nextPageToken")
        return comments, next_page

    async def reply_to_comment(
        self, access_token: str, comment_external_id: str, text: str
    ) -> CommentActionResult:
        """Post a reply to a YouTube comment thread."""
        import httpx

        body = {
            "snippet": {
                "parentId": comment_external_id,
                "textOriginal": text,
            }
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{YOUTUBE_API_BASE}/comments",
                    params={"part": "snippet"},
                    json=body,
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=30.0,
                )
                resp.raise_for_status()
            logger.info("youtube_comment_replied", parent_id=comment_external_id)
            return CommentActionResult(success=True)
        except httpx.HTTPStatusError as exc:
            msg = f"YouTube reply failed: {exc.response.status_code}"
            logger.error("youtube_reply_error", parent_id=comment_external_id, status=exc.response.status_code)
            return CommentActionResult(success=False, error_message=msg)

    async def hide_comment(
        self, access_token: str, comment_external_id: str
    ) -> CommentActionResult:
        """Set moderation status to heldForReview (hide)."""
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{YOUTUBE_API_BASE}/comments/setModerationStatus",
                    params={
                        "id": comment_external_id,
                        "moderationStatus": "heldForReview",
                    },
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=30.0,
                )
                resp.raise_for_status()
            logger.info("youtube_comment_hidden", comment_id=comment_external_id)
            return CommentActionResult(success=True)
        except httpx.HTTPStatusError as exc:
            msg = f"YouTube hide failed: {exc.response.status_code}"
            logger.error("youtube_hide_error", comment_id=comment_external_id, status=exc.response.status_code)
            return CommentActionResult(success=False, error_message=msg)

    async def delete_comment(
        self, access_token: str, comment_external_id: str
    ) -> CommentActionResult:
        """Delete a YouTube comment."""
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.delete(
                    f"{YOUTUBE_API_BASE}/comments",
                    params={"id": comment_external_id},
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=30.0,
                )
                resp.raise_for_status()
            logger.info("youtube_comment_deleted", comment_id=comment_external_id)
            return CommentActionResult(success=True)
        except httpx.HTTPStatusError as exc:
            msg = f"YouTube delete failed: {exc.response.status_code}"
            logger.error("youtube_delete_error", comment_id=comment_external_id, status=exc.response.status_code)
            return CommentActionResult(success=False, error_message=msg)
