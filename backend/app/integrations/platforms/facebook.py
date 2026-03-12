"""Facebook Graph API adapter — comment methods (Phase 1-B, S9).

Uses Facebook Graph API v19.0.
- Get comments: GET /{page-id}/feed → GET /{post-id}/comments
- Reply: POST /{comment-id}/comments
- Hide: POST /{comment-id}?is_hidden=true
- Delete: DELETE /{comment-id}
"""

from datetime import datetime
from urllib.parse import urlencode

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

FB_AUTH_URL = "https://www.facebook.com/v19.0/dialog/oauth"
FB_TOKEN_URL = "https://graph.facebook.com/v19.0/oauth/access_token"
GRAPH_API_BASE = "https://graph.facebook.com/v19.0"

FACEBOOK_SCOPES = (
    "pages_show_list,"
    "pages_read_engagement,"
    "pages_manage_posts,"
    "pages_manage_engagement,"
    "pages_read_user_content"
)


class FacebookAdapter(PlatformAdapter):
    def __init__(self, app_id: str, app_secret: str) -> None:
        self._app_id = app_id
        self._app_secret = app_secret

    # ── OAuth ─────────────────────────────────────────────

    async def get_auth_url(self, redirect_uri: str, state: str) -> str:
        params = {
            "client_id": self._app_id,
            "redirect_uri": redirect_uri,
            "scope": FACEBOOK_SCOPES,
            "response_type": "code",
            "state": state,
        }
        return f"{FB_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> TokenInfo:
        async with httpx.AsyncClient() as client:
            # Short-lived user token
            resp = await client.get(
                FB_TOKEN_URL,
                params={
                    "client_id": self._app_id,
                    "client_secret": self._app_secret,
                    "redirect_uri": redirect_uri,
                    "code": code,
                },
                timeout=30.0,
            )
            if resp.status_code != 200:
                logger.error("fb_exchange_code_failed", status=resp.status_code, body=resp.text[:500])
            resp.raise_for_status()
            data = resp.json()

            # Exchange for long-lived user token
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
            if ll_resp.status_code != 200:
                logger.error("fb_long_lived_token_failed", status=ll_resp.status_code, body=ll_resp.text[:500])
            ll_resp.raise_for_status()
            ll_data = ll_resp.json()

        return TokenInfo(
            access_token=ll_data["access_token"],
            refresh_token=None,
            expires_in=ll_data.get("expires_in", 5184000),
        )

    async def refresh_token(self, refresh_token: str) -> TokenInfo:
        # Facebook long-lived page tokens don't expire; user tokens are refreshed
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GRAPH_API_BASE}/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": self._app_id,
                    "client_secret": self._app_secret,
                    "fb_exchange_token": refresh_token,
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
                    "fields": "id,name,link,fan_count,about",
                    "access_token": access_token,
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
        return ChannelInfo(
            platform_account_id=data["id"],
            name=data.get("name", ""),
            profile_url=data.get("link"),
            followers_count=data.get("fan_count", 0),
            metadata={"about": data.get("about", "")},
        )

    async def publish(self, access_token: str, content: dict) -> PublishResult:
        """Post to Facebook Page feed via Graph API."""
        try:
            page_id = content.get("channel_account_id", "me")
            title = content.get("title", "")
            body = content.get("body", "")
            message = f"{title}\n\n{body}" if title and body else (body or title)

            params: dict = {
                "message": message,
                "access_token": access_token,
            }
            # 이미지 URL이 있으면 link 첨부
            media_urls = content.get("media_urls", [])
            if media_urls:
                params["link"] = media_urls[0]

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{GRAPH_API_BASE}/{page_id}/feed",
                    params=params,
                    timeout=30.0,
                )
                resp.raise_for_status()
                data = resp.json()
                post_id = data.get("id")

            logger.info("facebook_published", post_id=post_id, page_id=page_id)
            return PublishResult(
                success=True,
                platform_post_id=post_id,
                platform_url=f"https://facebook.com/{post_id}" if post_id else None,
            )
        except httpx.HTTPStatusError as exc:
            error_body = exc.response.text[:300] if exc.response else ""
            logger.error("facebook_publish_failed", status=exc.response.status_code, body=error_body)
            return PublishResult(
                success=False,
                error_message=f"Facebook publish failed: {exc.response.status_code} - {error_body}",
            )
        except Exception as exc:
            logger.error("facebook_publish_error", error=str(exc))
            return PublishResult(success=False, error_message=f"Facebook error: {exc!s}")

    async def validate_content(self, content: dict) -> list[ContentValidationError]:
        errors = []
        body = content.get("body", "")
        if len(body) > 63206:
            errors.append(ContentValidationError("body", "Facebook 게시글은 63,206자를 초과할 수 없습니다"))
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
        """Fetch comments from recent posts of the Facebook page."""
        comments: list[CommentData] = []
        next_page: str | None = None

        try:
            async with httpx.AsyncClient() as client:
                # 1. Get recent posts
                feed_params: dict = {
                    "fields": "id",
                    "limit": 10,
                    "access_token": access_token,
                }
                if page_token:
                    feed_params["after"] = page_token

                feed_resp = await client.get(
                    f"{GRAPH_API_BASE}/{channel_id}/feed",
                    params=feed_params,
                    timeout=30.0,
                )
                feed_resp.raise_for_status()
                feed_data = feed_resp.json()

                # 2. For each post, fetch comments
                since_param = {}
                if since:
                    since_param["since"] = str(int(since.timestamp()))

                for post_item in feed_data.get("data", []):
                    post_id = post_item["id"]
                    comment_params: dict = {
                        "fields": "id,message,from{name,id},created_time,parent{id}",
                        "limit": min(max_results, 50),
                        "access_token": access_token,
                        **since_param,
                    }
                    comment_resp = await client.get(
                        f"{GRAPH_API_BASE}/{post_id}/comments",
                        params=comment_params,
                        timeout=30.0,
                    )
                    comment_resp.raise_for_status()
                    comment_data = comment_resp.json()

                    for item in comment_data.get("data", []):
                        ts = item.get("created_time")
                        created_at = (
                            datetime.fromisoformat(ts.replace("Z", "+00:00"))
                            if ts
                            else None
                        )
                        from_data = item.get("from", {})
                        parent = item.get("parent")

                        comments.append(
                            CommentData(
                                external_id=item["id"],
                                text=item.get("message", ""),
                                author_name=from_data.get("name", ""),
                                author_profile_url=None,
                                parent_external_id=parent["id"] if parent else None,
                                platform_created_at=created_at,
                            )
                        )

                # Cursor pagination for feed
                paging = feed_data.get("paging", {})
                cursors = paging.get("cursors", {})
                if paging.get("next"):
                    next_page = cursors.get("after")

        except httpx.HTTPStatusError as exc:
            logger.error(
                "facebook_get_comments_error",
                status=exc.response.status_code,
                channel_id=channel_id,
            )
        except Exception as exc:
            logger.error("facebook_get_comments_error", error=str(exc))

        return comments, next_page

    async def reply_to_comment(
        self, access_token: str, comment_external_id: str, text: str
    ) -> CommentActionResult:
        """Reply to a Facebook comment."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{GRAPH_API_BASE}/{comment_external_id}/comments",
                    params={"message": text, "access_token": access_token},
                    timeout=30.0,
                )
                resp.raise_for_status()
            logger.info("facebook_comment_replied", comment_id=comment_external_id)
            return CommentActionResult(success=True)
        except httpx.HTTPStatusError as exc:
            msg = f"Facebook reply failed: {exc.response.status_code}"
            logger.error("facebook_reply_error", comment_id=comment_external_id, status=exc.response.status_code)
            return CommentActionResult(success=False, error_message=msg)

    async def hide_comment(
        self, access_token: str, comment_external_id: str
    ) -> CommentActionResult:
        """Hide a Facebook comment (set is_hidden=true)."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{GRAPH_API_BASE}/{comment_external_id}",
                    params={"is_hidden": "true", "access_token": access_token},
                    timeout=30.0,
                )
                resp.raise_for_status()
            logger.info("facebook_comment_hidden", comment_id=comment_external_id)
            return CommentActionResult(success=True)
        except httpx.HTTPStatusError as exc:
            msg = f"Facebook hide failed: {exc.response.status_code}"
            logger.error("facebook_hide_error", comment_id=comment_external_id, status=exc.response.status_code)
            return CommentActionResult(success=False, error_message=msg)

    async def delete_comment(
        self, access_token: str, comment_external_id: str
    ) -> CommentActionResult:
        """Delete a Facebook comment."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.delete(
                    f"{GRAPH_API_BASE}/{comment_external_id}",
                    params={"access_token": access_token},
                    timeout=30.0,
                )
                resp.raise_for_status()
            logger.info("facebook_comment_deleted", comment_id=comment_external_id)
            return CommentActionResult(success=True)
        except httpx.HTTPStatusError as exc:
            msg = f"Facebook delete failed: {exc.response.status_code}"
            logger.error("facebook_delete_error", comment_id=comment_external_id, status=exc.response.status_code)
            return CommentActionResult(success=False, error_message=msg)
