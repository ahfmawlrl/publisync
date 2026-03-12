"""Instagram Graph API adapter — comment methods (Phase 1-B, S9).

Uses Meta's Instagram Graph API v19.0.
- Get comments: GET /{ig-user-id}/media → GET /{media-id}/comments
- Reply: POST /{comment-id}/replies
- Hide: POST /{comment-id}?hide=true
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

# Facebook Login OAuth (for Instagram Business accounts via Facebook Pages)
FB_AUTH_URL = "https://www.facebook.com/v19.0/dialog/oauth"
FB_TOKEN_URL = "https://graph.facebook.com/v19.0/oauth/access_token"
FB_GRAPH_BASE = "https://graph.facebook.com/v19.0"

# New-style scope names (instagram_business_* instead of instagram_*)
INSTAGRAM_SCOPES = (
    "instagram_business_basic,"
    "instagram_manage_comments,"
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
        return f"{FB_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> TokenInfo:
        async with httpx.AsyncClient() as client:
            # Step 1: Exchange code for short-lived token
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
                logger.error("ig_exchange_code_failed", status=resp.status_code, body=resp.text[:500])
            resp.raise_for_status()
            data = resp.json()

            # Step 2: Exchange for long-lived token
            ll_resp = await client.get(
                f"{FB_GRAPH_BASE}/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": self._app_id,
                    "client_secret": self._app_secret,
                    "fb_exchange_token": data["access_token"],
                },
                timeout=30.0,
            )
            if ll_resp.status_code != 200:
                logger.error("ig_long_lived_token_failed", status=ll_resp.status_code, body=ll_resp.text[:500])
                # Fallback: use short-lived token
                return TokenInfo(
                    access_token=data["access_token"],
                    refresh_token=None,
                    expires_in=data.get("expires_in", 3600),
                )
            ll_data = ll_resp.json()
            logger.info("ig_token_exchanged")

        return TokenInfo(
            access_token=ll_data["access_token"],
            refresh_token=None,
            expires_in=ll_data.get("expires_in", 5184000),
        )

    async def refresh_token(self, refresh_token: str) -> TokenInfo:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{FB_GRAPH_BASE}/oauth/access_token",
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
            # Facebook Login → Pages → Instagram Business Account
            pages_resp = await client.get(
                f"{FB_GRAPH_BASE}/me/accounts",
                params={"fields": "id,name,instagram_business_account", "access_token": access_token},
                timeout=30.0,
            )
            if pages_resp.status_code != 200:
                logger.error("ig_pages_failed", status=pages_resp.status_code, body=pages_resp.text[:500])
            pages_resp.raise_for_status()
            pages = pages_resp.json().get("data", [])

            # Find first page with Instagram business account
            for page in pages:
                ig_account = page.get("instagram_business_account")
                if ig_account:
                    ig_resp = await client.get(
                        f"{FB_GRAPH_BASE}/{ig_account['id']}",
                        params={
                            "fields": "id,username,name,profile_picture_url,followers_count,biography",
                            "access_token": access_token,
                        },
                        timeout=30.0,
                    )
                    ig_resp.raise_for_status()
                    data = ig_resp.json()
                    return ChannelInfo(
                        platform_account_id=data["id"],
                        name=data.get("username") or data.get("name", ""),
                        profile_url=f"https://instagram.com/{data.get('username', '')}",
                        followers_count=data.get("followers_count", 0),
                        metadata={"biography": data.get("biography", "")},
                    )

            # Fallback: use Facebook page info or /me
            if pages:
                page = pages[0]
                return ChannelInfo(
                    platform_account_id=page["id"],
                    name=page.get("name", "Instagram Account"),
                    profile_url="https://instagram.com",
                    followers_count=0,
                    metadata={"note": "No Instagram Business Account linked to this Facebook Page"},
                )

            me_resp = await client.get(
                f"{FB_GRAPH_BASE}/me", params={"fields": "id,name", "access_token": access_token}, timeout=30.0
            )
            me_resp.raise_for_status()
            me = me_resp.json()
            return ChannelInfo(
                platform_account_id=me["id"],
                name=me.get("name", "Instagram Account"),
                profile_url="https://instagram.com",
                followers_count=0,
                metadata={"note": "No Facebook Pages found."},
            )

    async def publish(self, access_token: str, content: dict) -> PublishResult:
        """Publish to Instagram via Content Publishing API (2-step container flow).

        Instagram requires at least one image. If no media_urls are provided,
        returns a descriptive error (Fallback principle).
        """
        media_urls = content.get("media_urls", [])
        if not media_urls:
            return PublishResult(
                success=False,
                error_message="Instagram은 이미지 없이 게시할 수 없습니다. 미디어를 첨부해 주세요.",
            )

        ig_user_id = content.get("channel_account_id", "me")
        caption = content.get("body", "")
        title = content.get("title", "")
        if title and caption:
            caption = f"{title}\n\n{caption}"
        elif title:
            caption = title

        try:
            async with httpx.AsyncClient() as client:
                # Step 1: Create media container
                container_params: dict = {
                    "image_url": media_urls[0],
                    "caption": caption[:2200],  # Instagram 캡션 2200자 제한
                    "access_token": access_token,
                }
                container_resp = await client.post(
                    f"{FB_GRAPH_BASE}/{ig_user_id}/media",
                    params=container_params,
                    timeout=30.0,
                )
                container_resp.raise_for_status()
                container_id = container_resp.json().get("id")

                if not container_id:
                    return PublishResult(
                        success=False,
                        error_message="Instagram 미디어 컨테이너 생성 실패 (container_id 없음)",
                    )

                # Step 2: Publish the container
                publish_resp = await client.post(
                    f"{FB_GRAPH_BASE}/{ig_user_id}/media_publish",
                    params={
                        "creation_id": container_id,
                        "access_token": access_token,
                    },
                    timeout=60.0,  # 미디어 처리에 시간이 걸릴 수 있음
                )
                publish_resp.raise_for_status()
                media_id = publish_resp.json().get("id")

            logger.info("instagram_published", media_id=media_id, ig_user_id=ig_user_id)
            return PublishResult(
                success=True,
                platform_post_id=media_id,
                platform_url=f"https://instagram.com/p/{media_id}" if media_id else None,
            )
        except httpx.HTTPStatusError as exc:
            error_body = exc.response.text[:300] if exc.response else ""
            logger.error("instagram_publish_failed", status=exc.response.status_code, body=error_body)
            return PublishResult(
                success=False,
                error_message=f"Instagram publish failed: {exc.response.status_code} - {error_body}",
            )
        except Exception as exc:
            logger.error("instagram_publish_error", error=str(exc))
            return PublishResult(success=False, error_message=f"Instagram error: {exc!s}")

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
                    f"{FB_GRAPH_BASE}/{channel_id}/media",
                    params=media_params,
                    timeout=30.0,
                )
                media_resp.raise_for_status()
                media_data = media_resp.json()

                # 2. For each media, fetch comments
                for media_item in media_data.get("data", []):
                    media_id = media_item["id"]
                    comment_resp = await client.get(
                        f"{FB_GRAPH_BASE}/{media_id}/comments",
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
                    f"{FB_GRAPH_BASE}/{comment_external_id}/replies",
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
                    f"{FB_GRAPH_BASE}/{comment_external_id}",
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
                    f"{FB_GRAPH_BASE}/{comment_external_id}",
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
