"""Instagram Graph API adapter — comment methods (Phase 1-B, S9).

Uses Meta's Instagram Graph API v19.0.
- Get comments: GET /{ig-user-id}/media → GET /{media-id}/comments
- Reply: POST /{comment-id}/replies
- Hide: POST /{comment-id}?hide=true
- Delete: DELETE /{comment-id}
"""

from datetime import datetime

import httpx
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

META_AUTH_URL = "https://www.facebook.com/v19.0/dialog/oauth"
META_TOKEN_URL = "https://graph.facebook.com/v19.0/oauth/access_token"
GRAPH_API_BASE = "https://graph.facebook.com/v19.0"

INSTAGRAM_SCOPES = (
    "instagram_basic,"
    "instagram_manage_comments,"
    "instagram_manage_insights,"
    "instagram_content_publish,"
    "pages_show_list,"
    "pages_read_engagement"
)


class InstagramAdapter(PlatformAdapter):
    def __init__(self, app_id: str, app_secret: str) -> None:
        self._app_id = app_id
        self._app_secret = app_secret

    # ── OAuth ─────────────────────────────────────────────

    async def get_auth_url(self, redirect_uri: str, state: str) -> str:
        params = {
            "client_id": self._app_id,
            "redirect_uri": redirect_uri,
            "scope": INSTAGRAM_SCOPES,
            "response_type": "code",
            "state": state,
        }
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{META_AUTH_URL}?{qs}"

    async def exchange_code(self, code: str, redirect_uri: str) -> TokenInfo:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                META_TOKEN_URL,
                params={
                    "client_id": self._app_id,
                    "client_secret": self._app_secret,
                    "redirect_uri": redirect_uri,
                    "code": code,
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()

            # Exchange for long-lived token
            ll_resp = await client.get(
                f"{GRAPH_API_BASE}/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": self._app_id,
                    "client_secret": self._app_secret,
                    "fb_exchange_token": data["access_token"],
                },
                timeout=30.0,
            )
            ll_resp.raise_for_status()
            ll_data = ll_resp.json()

        return TokenInfo(
            access_token=ll_data["access_token"],
            refresh_token=None,
            expires_in=ll_data.get("expires_in", 5184000),
        )

    async def refresh_token(self, refresh_token: str) -> TokenInfo:
        # Instagram long-lived tokens are refreshed by calling the same endpoint
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GRAPH_API_BASE}/oauth/access_token",
                params={
                    "grant_type": "ig_refresh_token",
                    "access_token": refresh_token,
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
        return TokenInfo(
            access_token=data["access_token"],
            refresh_token=None,
            expires_in=data.get("expires_in", 5184000),
        )

    async def get_channel_info(self, access_token: str) -> ChannelInfo:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GRAPH_API_BASE}/me",
                params={
                    "fields": "id,username,name,profile_picture_url,followers_count,biography",
                    "access_token": access_token,
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
        return ChannelInfo(
            platform_account_id=data["id"],
            name=data.get("username") or data.get("name", ""),
            profile_url=f"https://instagram.com/{data.get('username', '')}",
            followers_count=data.get("followers_count", 0),
            metadata={"biography": data.get("biography", "")},
        )

    async def publish(self, access_token: str, content: dict) -> PublishResult:
        return PublishResult(
            success=False,
            error_message="Instagram publish requires media container creation (Phase 2)",
        )

    async def validate_content(self, content: dict) -> list[ContentValidationError]:
        errors = []
        body = content.get("body", "")
        if len(body) > 2200:
            errors.append(ContentValidationError("body", "Instagram 캡션은 2,200자를 초과할 수 없습니다"))
        hashtags = body.count("#")
        if hashtags > 30:
            errors.append(ContentValidationError("body", "Instagram 해시태그는 30개를 초과할 수 없습니다"))
        return errors

    def get_rate_limit_config(self) -> dict:
        return {"requests_per_hour": 200, "window": "1h"}

    # ── Comment methods ───────────────────────────────────

    async def get_comments(
        self,
        access_token: str,
        channel_id: str,
        since: datetime | None = None,
        page_token: str | None = None,
        max_results: int = 100,
    ) -> tuple[list[CommentData], str | None]:
        """Fetch comments from recent media of the Instagram business account."""
        comments: list[CommentData] = []
        next_page: str | None = None

        try:
            async with httpx.AsyncClient() as client:
                # 1. Get recent media
                media_params: dict = {
                    "fields": "id",
                    "limit": 10,
                    "access_token": access_token,
                }
                if page_token:
                    media_params["after"] = page_token

                media_resp = await client.get(
                    f"{GRAPH_API_BASE}/{channel_id}/media",
                    params=media_params,
                    timeout=30.0,
                )
                media_resp.raise_for_status()
                media_data = media_resp.json()

                # 2. For each media, fetch comments
                for media_item in media_data.get("data", []):
                    media_id = media_item["id"]
                    comment_resp = await client.get(
                        f"{GRAPH_API_BASE}/{media_id}/comments",
                        params={
                            "fields": "id,text,username,timestamp",
                            "limit": min(max_results, 50),
                            "access_token": access_token,
                        },
                        timeout=30.0,
                    )
                    comment_resp.raise_for_status()
                    comment_data = comment_resp.json()

                    for item in comment_data.get("data", []):
                        ts = item.get("timestamp")
                        created_at = (
                            datetime.fromisoformat(ts.replace("Z", "+00:00"))
                            if ts
                            else None
                        )
                        if since and created_at and created_at <= since:
                            continue

                        comments.append(
                            CommentData(
                                external_id=item["id"],
                                text=item.get("text", ""),
                                author_name=item.get("username", ""),
                                author_profile_url=None,
                                parent_external_id=None,
                                platform_created_at=created_at,
                            )
                        )

                # Cursor pagination for media
                paging = media_data.get("paging", {})
                cursors = paging.get("cursors", {})
                if paging.get("next"):
                    next_page = cursors.get("after")

        except httpx.HTTPStatusError as exc:
            logger.error(
                "instagram_get_comments_error",
                status=exc.response.status_code,
                channel_id=channel_id,
            )
        except Exception as exc:
            logger.error("instagram_get_comments_error", error=str(exc))

        return comments, next_page

    async def reply_to_comment(
        self, access_token: str, comment_external_id: str, text: str
    ) -> CommentActionResult:
        """Reply to an Instagram comment."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{GRAPH_API_BASE}/{comment_external_id}/replies",
                    params={"message": text, "access_token": access_token},
                    timeout=30.0,
                )
                resp.raise_for_status()
            logger.info("instagram_comment_replied", comment_id=comment_external_id)
            return CommentActionResult(success=True)
        except httpx.HTTPStatusError as exc:
            msg = f"Instagram reply failed: {exc.response.status_code}"
            logger.error("instagram_reply_error", comment_id=comment_external_id, status=exc.response.status_code)
            return CommentActionResult(success=False, error_message=msg)

    async def hide_comment(
        self, access_token: str, comment_external_id: str
    ) -> CommentActionResult:
        """Hide an Instagram comment."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{GRAPH_API_BASE}/{comment_external_id}",
                    params={"hide": "true", "access_token": access_token},
                    timeout=30.0,
                )
                resp.raise_for_status()
            logger.info("instagram_comment_hidden", comment_id=comment_external_id)
            return CommentActionResult(success=True)
        except httpx.HTTPStatusError as exc:
            msg = f"Instagram hide failed: {exc.response.status_code}"
            logger.error("instagram_hide_error", comment_id=comment_external_id, status=exc.response.status_code)
            return CommentActionResult(success=False, error_message=msg)

    async def delete_comment(
        self, access_token: str, comment_external_id: str
    ) -> CommentActionResult:
        """Delete an Instagram comment."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.delete(
                    f"{GRAPH_API_BASE}/{comment_external_id}",
                    params={"access_token": access_token},
                    timeout=30.0,
                )
                resp.raise_for_status()
            logger.info("instagram_comment_deleted", comment_id=comment_external_id)
            return CommentActionResult(success=True)
        except httpx.HTTPStatusError as exc:
            msg = f"Instagram delete failed: {exc.response.status_code}"
            logger.error("instagram_delete_error", comment_id=comment_external_id, status=exc.response.status_code)
            return CommentActionResult(success=False, error_message=msg)
