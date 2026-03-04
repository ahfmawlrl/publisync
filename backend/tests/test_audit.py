"""Audit log endpoint tests."""

import pytest
from httpx import AsyncClient


class TestAuditLogEndpoints:
    async def test_list_audit_logs_unauthorized(self, client: AsyncClient) -> None:
        """GET /audit-logs without auth should return 400 (missing Authorization header)."""
        resp = await client.get("/api/v1/audit-logs")
        assert resp.status_code == 400

    async def test_export_audit_logs_unauthorized(self, client: AsyncClient) -> None:
        """GET /audit-logs/export without auth should return 400."""
        resp = await client.get(
            "/api/v1/audit-logs/export",
            params={"start_date": "2025-01-01", "end_date": "2025-12-31"},
        )
        assert resp.status_code == 400

    async def test_get_audit_log_unauthorized(self, client: AsyncClient) -> None:
        """GET /audit-logs/{id} without auth should return 400."""
        resp = await client.get(
            "/api/v1/audit-logs/00000000-0000-0000-0000-000000000001"
        )
        assert resp.status_code == 400

    async def test_response_format(self, client: AsyncClient) -> None:
        """Error responses should follow API response format."""
        resp = await client.get("/api/v1/audit-logs")
        data = resp.json()
        assert data["success"] is False
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
