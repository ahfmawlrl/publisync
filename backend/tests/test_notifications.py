"""Notifications endpoint tests."""

from httpx import AsyncClient


class TestNotificationsEndpoints:
    async def test_list_notifications_unauthorized(self, client: AsyncClient) -> None:
        """GET /notifications without auth should return 400 (missing Authorization header)."""
        resp = await client.get("/api/v1/notifications")
        assert resp.status_code == 400

    async def test_unread_count_unauthorized(self, client: AsyncClient) -> None:
        """GET /notifications/unread-count without auth should return 400."""
        resp = await client.get("/api/v1/notifications/unread-count")
        assert resp.status_code == 400

    async def test_mark_all_read_unauthorized(self, client: AsyncClient) -> None:
        """POST /notifications/mark-all-read without auth should return 400."""
        resp = await client.post("/api/v1/notifications/mark-all-read")
        assert resp.status_code == 400

    async def test_mark_single_read_unauthorized(self, client: AsyncClient) -> None:
        """PATCH /notifications/{id}/read without auth should return 400."""
        resp = await client.patch(
            "/api/v1/notifications/00000000-0000-0000-0000-000000000001/read"
        )
        assert resp.status_code == 400

    async def test_response_format(self, client: AsyncClient) -> None:
        """Error responses should follow API response format."""
        resp = await client.get("/api/v1/notifications")
        data = resp.json()
        assert data["success"] is False
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
