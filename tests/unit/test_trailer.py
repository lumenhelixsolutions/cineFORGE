"""Unit tests for trailer generation endpoints."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from backend.app import app


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestGenerateTrailer:
    @pytest.mark.asyncio
    async def test_returns_404_for_missing_project(self, client: AsyncClient) -> None:
        resp = await client.post("/api/projects/nonexistent/generate-trailer")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Project not found"

    @pytest.mark.asyncio
    async def test_generates_trailer_with_treatment(self, client: AsyncClient) -> None:
        # Create project
        create_resp = await client.post("/projects", json={"name": "Trailer Test"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

        # Mock the bridge
        mock_bridge = MagicMock()
        mock_bridge.generate_video.return_value = {"task_id": "mpt-task-123", "status": "queued"}

        with patch("backend.app.get_bridge", return_value=mock_bridge):
            resp = await client.post(f"/api/projects/{project_id}/generate-trailer")

        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "mpt-task-123"
        assert data["status"] == "queued"

        # Verify bridge called with fallback logline (no treatment/sources)
        mock_bridge.generate_video.assert_called_once()
        call_kwargs = mock_bridge.generate_video.call_args.kwargs
        assert "video_subject" in call_kwargs

    @pytest.mark.asyncio
    async def test_generates_trailer_with_source_fallback(self, client: AsyncClient) -> None:
        # Create project and upload a source
        create_resp = await client.post("/projects", json={"name": "Trailer Source Test"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

        # Mock ingest to avoid file system dependencies
        with patch("backend.app.ingest_document", return_value="A great story about space."):
            from pathlib import Path
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
                f.write(b"A great story about space.")
                tmp_path = f.name

            # Upload source via internal call to avoid file upload complexities
            # Instead we create a SourceDoc manually
            from backend.database import AsyncSessionLocal
            from backend.models.project import SourceDoc
            async with AsyncSessionLocal() as session:
                source = SourceDoc(
                    project_id=project_id,
                    kind="txt",
                    raw_path=tmp_path,
                    normalized_path=tmp_path,
                    extracted_text="A great story about space.",
                    word_count=6,
                )
                session.add(source)
                await session.commit()

        mock_bridge = MagicMock()
        mock_bridge.generate_video.return_value = {"task_id": "mpt-task-456", "status": "queued"}

        with patch("backend.app.get_bridge", return_value=mock_bridge):
            resp = await client.post(f"/api/projects/{project_id}/generate-trailer")

        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "mpt-task-456"

        # Verify fallback used source text as logline
        call_kwargs = mock_bridge.generate_video.call_args.kwargs
        assert call_kwargs["video_subject"] == "A great story about space."

        Path(tmp_path).unlink(missing_ok=True)


class TestTrailerStatus:
    @pytest.mark.asyncio
    async def test_returns_not_started_when_no_task(self, client: AsyncClient) -> None:
        create_resp = await client.post("/projects", json={"name": "Status Test"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

        resp = await client.get(f"/api/projects/{project_id}/trailer-status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "not_started"
        assert data["task_id"] is None

    @pytest.mark.asyncio
    async def test_returns_mpt_status(self, client: AsyncClient) -> None:
        create_resp = await client.post("/projects", json={"name": "Status Poll Test"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

        # Set task id manually via update
        await client.patch(f"/projects/{project_id}", json={"trailer_task_id": "task-789"})

        mock_bridge = MagicMock()
        mock_bridge.get_task.return_value = {
            "data": {"state": "completed", "progress": 1, "video_url": "http://mpt/trailer.mp4"}
        }

        with patch("backend.app.get_bridge", return_value=mock_bridge):
            resp = await client.get(f"/api/projects/{project_id}/trailer-status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["progress"] == 1
        assert data["url"] == "http://mpt/trailer.mp4"
        mock_bridge.get_task.assert_called_once_with("task-789")

    @pytest.mark.asyncio
    async def test_returns_404_for_missing_project(self, client: AsyncClient) -> None:
        resp = await client.get("/api/projects/nonexistent/trailer-status")
        assert resp.status_code == 404


class TestTrailerDownload:
    @pytest.mark.asyncio
    async def test_returns_url_when_ready(self, client: AsyncClient) -> None:
        create_resp = await client.post("/projects", json={"name": "Download Test"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

        await client.patch(
            f"/projects/{project_id}",
            json={"trailer_task_id": "task-abc", "trailer_url": "http://mpt/final.mp4"},
        )

        resp = await client.get(f"/api/projects/{project_id}/trailer-download")
        assert resp.status_code == 200
        data = resp.json()
        assert data["url"] == "http://mpt/final.mp4"
        assert data["task_id"] == "task-abc"

    @pytest.mark.asyncio
    async def test_returns_404_when_no_url(self, client: AsyncClient) -> None:
        create_resp = await client.post("/projects", json={"name": "No Trailer Test"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

        resp = await client.get(f"/api/projects/{project_id}/trailer-download")
        assert resp.status_code == 404
        assert "not ready" in resp.json()["detail"].lower() or "not generated" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_refreshes_from_mpt_when_no_url_but_has_task(self, client: AsyncClient) -> None:
        create_resp = await client.post("/projects", json={"name": "Refresh Download Test"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

        await client.patch(f"/projects/{project_id}", json={"trailer_task_id": "task-def"})

        mock_bridge = MagicMock()
        mock_bridge.get_task.return_value = {"data": {"video_url": "http://mpt/refreshed.mp4"}}

        with patch("backend.app.get_bridge", return_value=mock_bridge):
            resp = await client.get(f"/api/projects/{project_id}/trailer-download")

        assert resp.status_code == 200
        data = resp.json()
        assert data["url"] == "http://mpt/refreshed.mp4"
        mock_bridge.get_task.assert_called_once_with("task-def")
