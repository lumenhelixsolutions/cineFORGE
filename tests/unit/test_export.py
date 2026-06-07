"""Unit tests for export & distribution pipeline."""

from __future__ import annotations

import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

from backend.app import app


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def mock_sleep():
    with patch("asyncio.sleep", new=AsyncMock()):
        yield


class TestQueueExport:
    @pytest.mark.asyncio
    async def test_queue_export_job(self, client: AsyncClient, mock_sleep) -> None:
        create_resp = await client.post("/projects", json={"name": "Export Test"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

        resp = await client.post(f"/api/projects/{project_id}/export", json={"type": "edl"})
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        assert data["type"] == "edl"

    @pytest.mark.asyncio
    async def test_returns_404_for_missing_project(self, client: AsyncClient) -> None:
        resp = await client.post("/api/projects/nonexistent/export", json={"type": "mp4"})
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Project not found"

    @pytest.mark.asyncio
    async def test_returns_400_for_invalid_type(self, client: AsyncClient) -> None:
        create_resp = await client.post("/projects", json={"name": "Bad Export Type"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

        resp = await client.post(f"/api/projects/{project_id}/export", json={"type": "invalid"})
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid export type"


class TestListExports:
    @pytest.mark.asyncio
    async def test_list_exports_for_project(self, client: AsyncClient, mock_sleep) -> None:
        create_resp = await client.post("/projects", json={"name": "List Exports Test"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

        # Queue two exports
        await client.post(f"/api/projects/{project_id}/export", json={"type": "edl"})
        await client.post(f"/api/projects/{project_id}/export", json={"type": "archive"})

        resp = await client.get(f"/api/projects/{project_id}/exports")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["type"] in ("edl", "archive")
        assert data[1]["type"] in ("edl", "archive")

    @pytest.mark.asyncio
    async def test_returns_404_for_missing_project(self, client: AsyncClient) -> None:
        resp = await client.get("/api/projects/nonexistent/exports")
        assert resp.status_code == 404


class TestExportProgress:
    @pytest.mark.asyncio
    async def test_progress_reaches_100(self, client: AsyncClient, mock_sleep) -> None:
        create_resp = await client.post("/projects", json={"name": "Progress Test"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

        resp = await client.post(f"/api/projects/{project_id}/export", json={"type": "edl"})
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]

        # With mocked sleep, the background task should complete immediately
        status_resp = await client.get(f"/api/exports/{job_id}")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["status"] == "completed"
        assert data["progress"] == 100.0
        assert data["output_url"] is not None


class TestDownloadExport:
    @pytest.mark.asyncio
    async def test_download_completed_export(self, client: AsyncClient, mock_sleep) -> None:
        create_resp = await client.post("/projects", json={"name": "Download Test"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

        resp = await client.post(f"/api/projects/{project_id}/export", json={"type": "edl"})
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]

        download_resp = await client.get(f"/api/exports/{job_id}/download")
        assert download_resp.status_code == 200
        assert download_resp.headers["content-type"].startswith("text/plain")
        content = download_resp.text
        assert "TITLE:" in content
        assert "FCM: NON-DROP FRAME" in content

    @pytest.mark.asyncio
    async def test_download_not_ready_returns_400(self, client: AsyncClient) -> None:
        # Create a job directly without running the background task
        create_resp = await client.post("/projects", json={"name": "Not Ready Test"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

        from backend.database import AsyncSessionLocal
        from backend.models.project import ExportJob
        async with AsyncSessionLocal() as session:
            job = ExportJob(project_id=project_id, type="mp4", status="processing", progress=50.0)
            session.add(job)
            await session.commit()
            job_id = job.id

        resp = await client.get(f"/api/exports/{job_id}/download")
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Export not ready"

    @pytest.mark.asyncio
    async def test_download_missing_job_returns_404(self, client: AsyncClient) -> None:
        resp = await client.get("/api/exports/nonexistent/download")
        assert resp.status_code == 404


class TestEdlFormat:
    @pytest.mark.asyncio
    async def test_edl_format_validation(self, client: AsyncClient, mock_sleep) -> None:
        create_resp = await client.post("/projects", json={"name": "EDL Format Test"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

        # Add shots with various transitions
        from backend.database import AsyncSessionLocal
        from backend.models.project import Shot
        async with AsyncSessionLocal() as session:
            for i, transition in enumerate(["hard_cut", "cross_dissolve", "whip_pan"]):
                shot = Shot(
                    project_id=project_id,
                    order_index=i,
                    duration_sec=5,
                    tier="standard",
                    prompt_text=f"Shot {i}",
                    bridge_strategy=transition,
                    transition_in=transition,
                )
                session.add(shot)
            await session.commit()

        resp = await client.post(f"/api/projects/{project_id}/export", json={"type": "edl"})
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]

        download_resp = await client.get(f"/api/exports/{job_id}/download")
        assert download_resp.status_code == 200
        edl = download_resp.text

        # CMX3600 validation
        lines = [line for line in edl.split("\n") if line.strip()]
        assert any(line.startswith("TITLE:") for line in lines)
        assert any("FCM: NON-DROP FRAME" in line for line in lines)

        # Check event lines
        event_lines = [line for line in lines if line[:3].isdigit()]
        assert len(event_lines) == 3

        # Verify transitions
        assert any("  C        " in line for line in event_lines)
        assert any("  D    030 " in line for line in event_lines)
        assert any("  W    030 " in line for line in event_lines)

        # Verify source/record timecodes
        for line in event_lines:
            parts = line.split()
            assert len(parts) >= 6
            tc_parts = [p for p in parts if ":" in p and len(p.split(":")) == 4]
            assert len(tc_parts) == 4  # source in, source out, record in, record out

        # Verify FROM CLIP NAME comments
        assert "* FROM CLIP NAME:" in edl


class TestArchiveExport:
    @pytest.mark.asyncio
    async def test_archive_zip_creation(self, client: AsyncClient, mock_sleep) -> None:
        create_resp = await client.post("/projects", json={"name": "Archive Test"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

        resp = await client.post(f"/api/projects/{project_id}/export", json={"type": "archive"})
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]

        status_resp = await client.get(f"/api/exports/{job_id}")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["status"] == "completed"
        assert data["output_size"] > 0

        # Validate ZIP contents
        zip_path = Path(data["output_url"])
        assert zip_path.exists()
        assert zip_path.suffix == ".zip"
        with zipfile.ZipFile(zip_path, "r") as zf:
            assert "project.json" in zf.namelist()


class TestStillsExport:
    @pytest.mark.asyncio
    async def test_stills_zip_contains_pngs(self, client: AsyncClient, mock_sleep) -> None:
        create_resp = await client.post("/projects", json={"name": "Stills Test"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

        # Add shots
        from backend.database import AsyncSessionLocal
        from backend.models.project import Shot
        async with AsyncSessionLocal() as session:
            for i in range(3):
                shot = Shot(
                    project_id=project_id,
                    order_index=i,
                    duration_sec=4,
                    tier="standard",
                    prompt_text=f"Shot {i}",
                )
                session.add(shot)
            await session.commit()

        resp = await client.post(f"/api/projects/{project_id}/export", json={"type": "stills"})
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]

        download_resp = await client.get(f"/api/exports/{job_id}/download")
        assert download_resp.status_code == 200
        assert download_resp.headers["content-type"] == "application/zip"

        zip_path = Path((await client.get(f"/api/exports/{job_id}")).json()["output_url"])
        assert zip_path.exists()
        with zipfile.ZipFile(zip_path, "r") as zf:
            pngs = [name for name in zf.namelist() if name.endswith(".png")]
            assert len(pngs) == 3


class TestCancelExport:
    @pytest.mark.asyncio
    async def test_cancel_job(self, client: AsyncClient, mock_sleep) -> None:
        create_resp = await client.post("/projects", json={"name": "Cancel Test"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

        resp = await client.post(f"/api/projects/{project_id}/export", json={"type": "edl"})
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]

        delete_resp = await client.delete(f"/api/exports/{job_id}")
        assert delete_resp.status_code == 200
        assert delete_resp.json()["status"] == "deleted"

        # Verify job is gone
        get_resp = await client.get(f"/api/exports/{job_id}")
        assert get_resp.status_code == 404


class TestExportNotFound:
    @pytest.mark.asyncio
    async def test_get_missing_job_returns_404(self, client: AsyncClient) -> None:
        resp = await client.get("/api/exports/nonexistent")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Export job not found"

    @pytest.mark.asyncio
    async def test_delete_missing_job_returns_404(self, client: AsyncClient) -> None:
        resp = await client.delete("/api/exports/nonexistent")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Export job not found"
