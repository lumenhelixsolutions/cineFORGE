"""Security hardening tests for CineForge backend."""

from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from backend.app import app
from backend.middleware import clear_rate_limits


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestSecurityHeaders:
    @pytest.mark.asyncio
    async def test_security_headers_present(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("X-XSS-Protection") == "1; mode=block"
        assert "default-src 'self'" in resp.headers.get("Content-Security-Policy", "")

    @pytest.mark.asyncio
    async def test_hsts_not_added_for_http(self, client: AsyncClient) -> None:
        """HSTS header should be omitted for plain HTTP requests."""
        resp = await client.get("/health")
        assert "Strict-Transport-Security" not in resp.headers


class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_generate_endpoint_rate_limit_triggers_429(self, client: AsyncClient) -> None:
        clear_rate_limits()
        # The endpoint requires a real project to exist, but the rate limiter
        # runs before the route handler.  We can hit any /api/.../generate path.
        for _ in range(5):
            resp = await client.post("/api/projects/nonexistent/generate-trailer")
            # 404 is expected because the project does not exist
            assert resp.status_code == 404

        # 6th request should be rate limited
        resp = await client.post("/api/projects/nonexistent/generate-trailer")
        assert resp.status_code == 429
        data = resp.json()
        assert "error" in data
        assert "Rate limit exceeded" in data["error"]
        clear_rate_limits()

    @pytest.mark.asyncio
    async def test_download_endpoint_rate_limit_triggers_429(self, client: AsyncClient) -> None:
        clear_rate_limits()
        for _ in range(20):
            resp = await client.get("/api/broll/nonexistent/download")
            # 404 because clip does not exist
            assert resp.status_code == 404

        # 21st request should be rate limited
        resp = await client.get("/api/broll/nonexistent/download")
        assert resp.status_code == 429
        data = resp.json()
        assert data["error"] == "Rate limit exceeded"
        clear_rate_limits()


class TestInputValidation:
    @pytest.mark.asyncio
    async def test_oversized_project_name_rejected(self, client: AsyncClient) -> None:
        resp = await client.post("/projects", json={"name": "x" * 201})
        assert resp.status_code == 422
        data = resp.json()
        assert "error" in data
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_invalid_target_duration_rejected(self, client: AsyncClient) -> None:
        resp = await client.post("/projects", json={"name": "Valid Name", "target_duration_sec": 0})
        assert resp.status_code == 422
        data = resp.json()
        assert "error" in data
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_negative_extra_seconds_rejected(self, client: AsyncClient) -> None:
        create_resp = await client.post("/projects", json={"name": "Extend Test"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

        resp = await client.post(
            f"/projects/{project_id}/extend",
            json={"shot_id": "fake-shot-id", "extra_seconds": -1},
        )
        assert resp.status_code == 422
        data = resp.json()
        assert "error" in data
        assert "detail" in data


class TestHtmlEscaping:
    @pytest.mark.asyncio
    async def test_html_in_shot_prompt_is_escaped(self, client: AsyncClient) -> None:
        from backend.database import AsyncSessionLocal
        from backend.models.project import Shot

        create_resp = await client.post("/projects", json={"name": "Escape Test"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

        async with AsyncSessionLocal() as session:
            shot = Shot(
                project_id=project_id,
                order_index=0,
                duration_sec=5,
                tier="standard",
                prompt_text="initial",
            )
            session.add(shot)
            await session.commit()
            shot_id = shot.id

        malicious = "<script>alert(1)</script>"
        resp = await client.patch(
            f"/projects/{project_id}/shots/{shot_id}",
            json={"prompt_text": malicious},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["prompt_text"] == "&lt;script&gt;alert(1)&lt;/script&gt;"

    @pytest.mark.asyncio
    async def test_html_in_project_name_is_escaped(self, client: AsyncClient) -> None:
        create_resp = await client.post("/projects", json={"name": "Normal Name"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

        malicious = "<b>bold</b>"
        resp = await client.patch(
            f"/projects/{project_id}",
            json={"name": malicious},
        )
        assert resp.status_code == 200

        # Verify the stored name is escaped
        get_resp = await client.get(f"/projects/{project_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "&lt;b&gt;bold&lt;/b&gt;"
