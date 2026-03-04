"""Comments endpoint tests."""

import pytest
from httpx import AsyncClient


class TestCommentsEndpoints:
    async def test_list_comments_unauthorized(self, client: AsyncClient) -> None:
        """GET /comments without auth should return 400 (missing Authorization header)."""
        resp = await client.get("/api/v1/comments")
        assert resp.status_code == 400

    async def test_dangerous_comments_unauthorized(self, client: AsyncClient) -> None:
        """GET /comments/dangerous without auth should return 400."""
        resp = await client.get("/api/v1/comments/dangerous")
        assert resp.status_code == 400

    async def test_get_comment_unauthorized(self, client: AsyncClient) -> None:
        """GET /comments/{id} without auth should return 400."""
        resp = await client.get(
            "/api/v1/comments/00000000-0000-0000-0000-000000000001"
        )
        assert resp.status_code == 400

    async def test_reply_comment_unauthorized(self, client: AsyncClient) -> None:
        """POST /comments/{id}/reply without auth should return 400."""
        resp = await client.post(
            "/api/v1/comments/00000000-0000-0000-0000-000000000001/reply",
            json={"text": "test reply"},
        )
        assert resp.status_code == 400

    async def test_hide_comment_unauthorized(self, client: AsyncClient) -> None:
        """POST /comments/{id}/hide without auth should return 400."""
        resp = await client.post(
            "/api/v1/comments/00000000-0000-0000-0000-000000000001/hide",
            json={"reason": "test reason"},
        )
        assert resp.status_code == 400

    async def test_response_format(self, client: AsyncClient) -> None:
        """Error responses should follow API response format."""
        resp = await client.get("/api/v1/comments")
        data = resp.json()
        assert data["success"] is False
        assert "error" in data
