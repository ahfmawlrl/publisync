"""AI endpoint tests."""

from httpx import AsyncClient


class TestAiEndpoints:
    async def test_generate_title_unauthorized(self, client: AsyncClient) -> None:
        """POST /ai/generate-title without auth should return 400 (missing Authorization header)."""
        resp = await client.post("/api/v1/ai/generate-title", json={
            "content_text": "test content text for title generation",
        })
        assert resp.status_code == 400

    async def test_generate_description_unauthorized(self, client: AsyncClient) -> None:
        """POST /ai/generate-description without auth should return 400."""
        resp = await client.post("/api/v1/ai/generate-description", json={
            "content_text": "test content text for description generation",
        })
        assert resp.status_code == 400

    async def test_generate_hashtags_unauthorized(self, client: AsyncClient) -> None:
        """POST /ai/generate-hashtags without auth should return 400."""
        resp = await client.post("/api/v1/ai/generate-hashtags", json={
            "content_text": "test content text for hashtag generation",
        })
        assert resp.status_code == 400

    async def test_generate_title_missing_body(self, client: AsyncClient) -> None:
        """POST /ai/generate-title with empty body should return 400."""
        resp = await client.post("/api/v1/ai/generate-title", json={})
        assert resp.status_code == 400

    async def test_generate_title_empty_content(self, client: AsyncClient) -> None:
        """POST /ai/generate-title with empty content_text should return 400."""
        resp = await client.post("/api/v1/ai/generate-title", json={
            "content_text": "",
        })
        assert resp.status_code == 400

    async def test_response_format(self, client: AsyncClient) -> None:
        """Error responses should follow API response format."""
        resp = await client.post("/api/v1/ai/generate-title", json={})
        data = resp.json()
        assert data["success"] is False
        assert "error" in data
