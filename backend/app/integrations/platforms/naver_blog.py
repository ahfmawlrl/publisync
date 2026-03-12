"""Naver Blog API adapter — comment methods (Phase 1-B, S9).

Uses Naver Open API for blog.
- Get comments: Naver Blog Comment API (limited access)
- Reply/Hide/Delete: Not officially supported by Naver Open API — uses web scraping
  fallback approach or returns not-supported errors.

Note: Naver Blog's public API is read-heavy. Write operations (reply, hide, delete)
require Naver Login + custom session handling which is limited by Naver's TOS.
For MVP, get_comments works via Open API; write operations require manual action
and are marked as not-supported with guidance.
"""

from datetime import datetime
from urllib.parse import quote

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

NAVER_AUTH_URL = "https://nid.naver.com/oauth2.0/authorize"
NAVER_TOKEN_URL = "https://nid.naver.com/oauth2.0/token"
NAVER_API_BASE = "https://openapi.naver.com"
NAVER_BLOG_API = "https://openapi.naver.com/blog"


class NaverBlogAdapter(PlatformAdapter):
    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

    # ── OAuth ─────────────────────────────────────────────

    async def get_auth_url(self, redirect_uri: str, state: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "state": state,
        }
        qs = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
        return f"{NAVER_AUTH_URL}?{qs}"

    async def exchange_code(self, code: str, redirect_uri: str) -> TokenInfo:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                NAVER_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "code": code,
                    "state": "publisync",
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
        return TokenInfo(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_in=int(data.get("expires_in", 3600)),
        )

    async def refresh_token(self, refresh_token: str) -> TokenInfo:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                NAVER_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "refresh_token": refresh_token,
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
        return TokenInfo(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", refresh_token),
            expires_in=int(data.get("expires_in", 3600)),
        )

    async def get_channel_info(self, access_token: str) -> ChannelInfo:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{NAVER_API_BASE}/v1/nid/me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json().get("response", {})
        blog_id = data.get("id", "")
        nickname = data.get("nickname", "")
        return ChannelInfo(
            platform_account_id=blog_id,
            name=nickname,
            profile_url=f"https://blog.naver.com/{nickname}" if nickname else None,
            followers_count=0,
            metadata={"email": data.get("email", "")},
        )

    async def publish(self, access_token: str, content: dict) -> PublishResult:
        """Write a blog post via Naver Blog Write API."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{NAVER_BLOG_API}/writePost.json",
                    headers={"Authorization": f"Bearer {access_token}"},
                    data={
                        "title": content.get("title", ""),
                        "contents": content.get("body", ""),
                    },
                    timeout=30.0,
                )
                resp.raise_for_status()
                data = resp.json()

                # Naver Blog API returns logNo in response
                log_no = data.get("logNo") or data.get("result", {}).get("logNo")
                blog_id = content.get("channel_account_id", "")
                platform_url = (
                    f"https://blog.naver.com/{blog_id}/{log_no}"
                    if blog_id and log_no
                    else None
                )

            logger.info("naver_blog_published", log_no=log_no, blog_id=blog_id)
            return PublishResult(
                success=True,
                platform_post_id=str(log_no) if log_no else None,
                platform_url=platform_url,
            )
        except httpx.HTTPStatusError as exc:
            error_body = exc.response.text[:300] if exc.response else ""
            logger.error("naver_blog_publish_failed", status=exc.response.status_code, body=error_body)
            return PublishResult(
                success=False,
                error_message=f"Naver Blog publish failed: {exc.response.status_code} - {error_body}",
            )
        except Exception as exc:
            logger.error("naver_blog_publish_error", error=str(exc))
            return PublishResult(success=False, error_message=f"Naver Blog error: {exc!s}")

    async def validate_content(self, content: dict) -> list[ContentValidationError]:
        errors = []
        title = content.get("title", "")
        if len(title) > 500:
            errors.append(ContentValidationError("title", "네이버 블로그 제목은 500자를 초과할 수 없습니다"))
        return errors

    def get_rate_limit_config(self) -> dict:
        return {"requests_per_day": 25000, "window": "24h"}

    # ── Comment methods ───────────────────────────────────

    async def get_comments(
        self,
        access_token: str,
        channel_id: str,
        since: datetime | None = None,
        page_token: str | None = None,
        max_results: int = 100,
    ) -> tuple[list[CommentData], str | None]:
        """Fetch comments from recent blog posts via Naver Blog Search API.

        Naver Blog doesn't have a direct "get all comments" API.
        We search for the blog's recent posts, then fetch comments per post
        using the blog comment list API.
        """
        comments: list[CommentData] = []
        next_page: str | None = None

        try:
            page_num = int(page_token) if page_token else 1
            async with httpx.AsyncClient() as client:
                # 1. Search for blog posts by this blogger
                search_resp = await client.get(
                    f"{NAVER_API_BASE}/v1/search/blog.json",
                    params={
                        "query": f"site:blog.naver.com/{channel_id}",
                        "display": 10,
                        "start": (page_num - 1) * 10 + 1,
                        "sort": "date",
                    },
                    headers={
                        "X-Naver-Client-Id": self._client_id,
                        "X-Naver-Client-Secret": self._client_secret,
                    },
                    timeout=30.0,
                )
                search_resp.raise_for_status()
                search_data = search_resp.json()

                items = search_data.get("items", [])
                total = search_data.get("total", 0)

                # 2. Extract post log numbers from URLs and fetch comments
                for item in items:
                    link = item.get("link", "")
                    # Extract logNo from blog.naver.com/blogger/logNo format
                    log_no = self._extract_log_no(link, channel_id)
                    if not log_no:
                        continue

                    comment_url = "https://apis.naver.com/cafe-web/cafe-mobile/CommentListByArticle.json"
                    comment_resp = await client.get(
                        comment_url,
                        params={
                            "ticket": "blog",
                            "templateId": "default",
                            "blogId": channel_id,
                            "logNo": log_no,
                            "page": 1,
                            "pageSize": min(max_results, 50),
                        },
                        headers={"Referer": f"https://blog.naver.com/{channel_id}/{log_no}"},
                        timeout=30.0,
                    )
                    if comment_resp.status_code != 200:
                        continue

                    comment_data = comment_resp.json()
                    for c in comment_data.get("result", {}).get("list", []):
                        ts = c.get("writeDate")
                        created_at = None
                        if ts:
                            try:
                                created_at = datetime.fromtimestamp(ts / 1000)
                            except (ValueError, TypeError):
                                pass

                        if since and created_at and created_at <= since:
                            continue

                        comments.append(
                            CommentData(
                                external_id=str(c.get("commentNo", "")),
                                text=c.get("content", ""),
                                author_name=c.get("writerNickName", c.get("writerId", "")),
                                author_profile_url=None,
                                parent_external_id=str(c.get("parentCommentNo")) if c.get("parentCommentNo") else None,
                                platform_created_at=created_at,
                            )
                        )

                # Pagination
                if (page_num * 10) < total:
                    next_page = str(page_num + 1)

        except httpx.HTTPStatusError as exc:
            logger.error(
                "naver_get_comments_error",
                status=exc.response.status_code,
                channel_id=channel_id,
            )
        except Exception as exc:
            logger.error("naver_get_comments_error", error=str(exc))

        return comments, next_page

    @staticmethod
    def _extract_log_no(url: str, blog_id: str) -> str | None:
        """Extract logNo from a Naver Blog post URL."""
        # Pattern: https://blog.naver.com/{blogId}/{logNo}
        try:
            parts = url.rstrip("/").split("/")
            if blog_id in parts:
                idx = parts.index(blog_id)
                if idx + 1 < len(parts):
                    return parts[idx + 1]
        except (ValueError, IndexError):
            pass
        return None

    async def reply_to_comment(
        self, access_token: str, comment_external_id: str, text: str
    ) -> CommentActionResult:
        """Reply to a Naver Blog comment.

        Note: Naver Blog does not provide an official comment reply API.
        This returns a not-supported result. Operators should reply manually
        via the Naver Blog admin interface.
        """
        return CommentActionResult(
            success=False,
            error_message=(
                "네이버 블로그 댓글 답글은 API로 지원되지 않습니다. "
                "네이버 블로그 관리 페이지에서 직접 답글을 작성해 주세요."
            ),
        )

    async def hide_comment(
        self, access_token: str, comment_external_id: str
    ) -> CommentActionResult:
        """Hide a Naver Blog comment.

        Note: Naver Blog does not provide a comment hide API.
        """
        return CommentActionResult(
            success=False,
            error_message=(
                "네이버 블로그 댓글 숨기기는 API로 지원되지 않습니다. "
                "네이버 블로그 관리 페이지에서 직접 처리해 주세요."
            ),
        )

    async def delete_comment(
        self, access_token: str, comment_external_id: str
    ) -> CommentActionResult:
        """Delete a Naver Blog comment.

        Note: Naver Blog does not provide a comment delete API.
        """
        return CommentActionResult(
            success=False,
            error_message=(
                "네이버 블로그 댓글 삭제는 API로 지원되지 않습니다. "
                "네이버 블로그 관리 페이지에서 직접 처리해 주세요."
            ),
        )
