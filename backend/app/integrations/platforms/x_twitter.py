"""X (Twitter) API v2 adapter — comment methods (Phase 1-B, S9).

Uses X API v2 with OAuth 2.0.
- Get mentions: GET /2/users/{id}/mentions
- Reply: POST /2/tweets (with reply.in_reply_to_tweet_id)
- Hide reply: PUT /2/tweets/{id}/hidden
- Delete tweet: DELETE /2/tweets/{id}
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

X_AUTH_URL = "https://twitter.com/i/oauth2/authorize"
X_TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
X_API_BASE = "https://api.twitter.com/2"

X_SCOPES = "tweet.read tweet.write tweet.moderate.write users.read offline.access"


class XTwitterAdapter(PlatformAdapter):
    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

    # ── OAuth 2.0 with PKCE ──────────────────────────────

    async def get_auth_url(self, redirect_uri: str, state: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "scope": X_SCOPES,
            "state": state,
            "code_challenge": "challenge",
            "code_challenge_method": "plain",
        }
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{X_AUTH_URL}?{qs}"

    async def exchange_code(self, code: str, redirect_uri: str) -> TokenInfo:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                X_TOKEN_URL,
                data={
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                    "code_verifier": "challenge",
                },
                auth=(self._client_id, self._client_secret),
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
        return TokenInfo(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_in=data.get("expires_in", 7200),
        )

    async def refresh_token(self, refresh_token: str) -> TokenInfo:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                X_TOKEN_URL,
                data={
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
                auth=(self._client_id, self._client_secret),
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
        return TokenInfo(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", refresh_token),
            expires_in=data.get("expires_in", 7200),
        )

    async def get_channel_info(self, access_token: str) -> ChannelInfo:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{X_API_BASE}/users/me",
                params={"user.fields": "id,name,username,profile_image_url,public_metrics,description"},
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
        metrics = data.get("public_metrics", {})
        return ChannelInfo(
            platform_account_id=data["id"],
            name=data.get("username", ""),
            profile_url=f"https://x.com/{data.get('username', '')}",
            followers_count=metrics.get("followers_count", 0),
            metadata={"description": data.get("description", "")},
        )

    async def publish(self, access_token: str, content: dict) -> PublishResult:
        return PublishResult(
            success=False,
            error_message="X publish not yet implemented",
        )

    async def validate_content(self, content: dict) -> list[ContentValidationError]:
        errors = []
        body = content.get("body", "")
        if len(body) > 280:
            errors.append(ContentValidationError("body", "X 게시글은 280자를 초과할 수 없습니다"))
        return errors

    def get_rate_limit_config(self) -> dict:
        return {"requests_per_15min": 300, "window": "15m"}

    # ── Comment methods (mentions/replies) ────────────────

    async def get_comments(
        self,
        access_token: str,
        channel_id: str,
        since: datetime | None = None,
        page_token: str | None = None,
        max_results: int = 100,
    ) -> tuple[list[CommentData], str | None]:
        """Fetch mentions (replies) for the authenticated user."""
        comments: list[CommentData] = []
        next_page: str | None = None

        try:
            params: dict = {
                "tweet.fields": "id,text,author_id,created_at,in_reply_to_user_id,conversation_id",
                "expansions": "author_id",
                "user.fields": "name,username,profile_image_url",
                "max_results": min(max_results, 100),
            }
            if page_token:
                params["pagination_token"] = page_token
            if since:
                params["start_time"] = since.strftime("%Y-%m-%dT%H:%M:%SZ")

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{X_API_BASE}/users/{channel_id}/mentions",
                    params=params,
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=30.0,
                )
                resp.raise_for_status()
                data = resp.json()

            # Build author lookup from includes
            users_map: dict[str, dict] = {}
            for user in data.get("includes", {}).get("users", []):
                users_map[user["id"]] = user

            for tweet in data.get("data", []):
                ts = tweet.get("created_at")
                created_at = (
                    datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if ts
                    else None
                )
                author = users_map.get(tweet.get("author_id", ""), {})

                comments.append(
                    CommentData(
                        external_id=tweet["id"],
                        text=tweet.get("text", ""),
                        author_name=author.get("username", author.get("name", "")),
                        author_profile_url=author.get("profile_image_url"),
                        parent_external_id=tweet.get("conversation_id"),
                        platform_created_at=created_at,
                    )
                )

            meta = data.get("meta", {})
            next_page = meta.get("next_token")

        except httpx.HTTPStatusError as exc:
            logger.error(
                "x_get_mentions_error",
                status=exc.response.status_code,
                channel_id=channel_id,
            )
        except Exception as exc:
            logger.error("x_get_mentions_error", error=str(exc))

        return comments, next_page

    async def reply_to_comment(
        self, access_token: str, comment_external_id: str, text: str
    ) -> CommentActionResult:
        """Reply to a tweet (post a tweet with in_reply_to_tweet_id)."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{X_API_BASE}/tweets",
                    json={
                        "text": text,
                        "reply": {"in_reply_to_tweet_id": comment_external_id},
                    },
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=30.0,
                )
                resp.raise_for_status()
            logger.info("x_tweet_replied", tweet_id=comment_external_id)
            return CommentActionResult(success=True)
        except httpx.HTTPStatusError as exc:
            msg = f"X reply failed: {exc.response.status_code}"
            logger.error("x_reply_error", tweet_id=comment_external_id, status=exc.response.status_code)
            return CommentActionResult(success=False, error_message=msg)

    async def hide_comment(
        self, access_token: str, comment_external_id: str
    ) -> CommentActionResult:
        """Hide a reply on X (PUT /tweets/{id}/hidden)."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.put(
                    f"{X_API_BASE}/tweets/{comment_external_id}/hidden",
                    json={"hidden": True},
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=30.0,
                )
                resp.raise_for_status()
            logger.info("x_tweet_hidden", tweet_id=comment_external_id)
            return CommentActionResult(success=True)
        except httpx.HTTPStatusError as exc:
            msg = f"X hide failed: {exc.response.status_code}"
            logger.error("x_hide_error", tweet_id=comment_external_id, status=exc.response.status_code)
            return CommentActionResult(success=False, error_message=msg)

    async def delete_comment(
        self, access_token: str, comment_external_id: str
    ) -> CommentActionResult:
        """Delete a tweet on X."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.delete(
                    f"{X_API_BASE}/tweets/{comment_external_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=30.0,
                )
                resp.raise_for_status()
            logger.info("x_tweet_deleted", tweet_id=comment_external_id)
            return CommentActionResult(success=True)
        except httpx.HTTPStatusError as exc:
            msg = f"X delete failed: {exc.response.status_code}"
            logger.error("x_delete_error", tweet_id=comment_external_id, status=exc.response.status_code)
            return CommentActionResult(success=False, error_message=msg)
