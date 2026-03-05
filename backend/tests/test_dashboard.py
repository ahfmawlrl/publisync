"""Dashboard endpoint tests."""

from httpx import AsyncClient


class TestDashboardEndpoints:
    async def test_summary_unauthorized(self, client: AsyncClient) -> None:
        """GET /dashboard/summary without auth should return 400 (missing Authorization header)."""
        resp = await client.get("/api/v1/dashboard/summary")
        assert resp.status_code == 400

    async def test_sentiment_summary_unauthorized(self, client: AsyncClient) -> None:
        """GET /dashboard/sentiment-summary without auth should return 400."""
        resp = await client.get("/api/v1/dashboard/sentiment-summary")
        assert resp.status_code == 400

    async def test_platform_trends_unauthorized(self, client: AsyncClient) -> None:
        """GET /dashboard/platform-trends without auth should return 400."""
        resp = await client.get("/api/v1/dashboard/platform-trends")
        assert resp.status_code == 400

    async def test_recent_contents_unauthorized(self, client: AsyncClient) -> None:
        """GET /dashboard/recent-contents without auth should return 400."""
        resp = await client.get("/api/v1/dashboard/recent-contents")
        assert resp.status_code == 400

    async def test_badge_counts_unauthorized(self, client: AsyncClient) -> None:
        """GET /dashboard/badge-counts without auth should return 400."""
        resp = await client.get("/api/v1/dashboard/badge-counts")
        assert resp.status_code == 400

    async def test_approval_status_unauthorized(self, client: AsyncClient) -> None:
        """GET /dashboard/approval-status without auth should return 400."""
        resp = await client.get("/api/v1/dashboard/approval-status")
        assert resp.status_code == 400

    async def test_today_schedule_unauthorized(self, client: AsyncClient) -> None:
        """GET /dashboard/today-schedule without auth should return 400."""
        resp = await client.get("/api/v1/dashboard/today-schedule")
        assert resp.status_code == 400

    async def test_all_organizations_unauthorized(self, client: AsyncClient) -> None:
        """GET /dashboard/all-organizations without auth should return 400."""
        resp = await client.get("/api/v1/dashboard/all-organizations")
        assert resp.status_code == 400

    async def test_response_format(self, client: AsyncClient) -> None:
        """Error responses should follow API response format with success=False."""
        resp = await client.get("/api/v1/dashboard/summary")
        data = resp.json()
        assert data["success"] is False
        assert "error" in data
