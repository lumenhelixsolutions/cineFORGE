"""Unit tests for B-roll generation endpoints."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from httpx import AsyncClient, ASGITransport

from backend.app import app
from backend.database import AsyncSessionLocal
from backend.models.project import Base


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
async def cleanup_db() -> None:
    yield
    async with AsyncSessionLocal() as session:
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()


class TestGenerateBroll:
    @pytest.mark.asyncio
    async def test_returns_404_for_missing_scene(self, client: AsyncClient) -> None:
        resp = await client.post("/api/scenes/nonexistent/generate-broll")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Scene not found"

    @pytest.mark.asyncio
    async def test_queues_broll_generation(self, client: AsyncClient) -> None:
        # Create project
        create_resp = await client.post("/projects", json={"name": "Broll Test"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

        # Create a shot directly
        from backend.models.project import Shot
        async with AsyncSessionLocal() as session:
            shot = Shot(
                project_id=project_id,
                order_index=0,
                duration_sec=6,
                tier="standard",
                prompt_text="Wide shot of a misty forest at dawn",
                continuity={"location": "forest", "mood": "serene", "time_of_day": "dawn"},
            )
            session.add(shot)
            await session.commit()
            shot_id = shot.id

        # Mock the bridge methods directly to avoid async HTTP complexity
        with patch.object(
            app.state.__class__,
            "registry",
            create=True,
        ):
            pass  # Not needed since we mock generate_for_shot

        with patch("backend.app.MPTBrollBridge.generate_for_shot", return_value={
            "clip_path": "/tmp/fake_broll.mp4",
            "thumbnail_path": "/tmp/fake_broll.jpg",
            "metadata": {"location": "forest", "mood": "serene", "time_of_day": "dawn"},
            "cost_usd": 0.0,
            "provider_id": "mpt",
            "prompt_text": "B-roll prompt",
            "duration_sec": 4.0,
        }):
            resp = await client.post(f"/api/scenes/{shot_id}/generate-broll")

        assert resp.status_code == 200
        data = resp.json()
        assert "clip_id" in data
        assert data["status"] == "queued"

    @pytest.mark.asyncio
    async def test_queues_broll_for_empty_prompt(self, client: AsyncClient) -> None:
        """B-Roll generation should queue even when the shot has an empty prompt."""
        create_resp = await client.post("/projects", json={"name": "Empty Prompt Broll Test"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

        from backend.models.project import Shot
        async with AsyncSessionLocal() as session:
            shot = Shot(
                project_id=project_id,
                order_index=0,
                duration_sec=6,
                tier="standard",
                prompt_text="",
                continuity={},
            )
            session.add(shot)
            await session.commit()
            shot_id = shot.id

        with patch("backend.app.MPTBrollBridge.generate_for_shot", return_value={
            "clip_path": "/tmp/fake_broll.mp4",
            "thumbnail_path": "/tmp/fake_broll.jpg",
            "metadata": {},
            "cost_usd": 0.0,
            "provider_id": "mpt",
            "prompt_text": "",
            "duration_sec": 4.0,
        }):
            resp = await client.post(f"/api/scenes/{shot_id}/generate-broll")

        assert resp.status_code == 200
        data = resp.json()
        assert "clip_id" in data
        assert data["status"] == "queued"

    @pytest.mark.asyncio
    async def test_lists_broll_for_scene(self, client: AsyncClient) -> None:
        create_resp = await client.post("/projects", json={"name": "List Broll Test"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

        from backend.models.project import Shot, BrollClip
        async with AsyncSessionLocal() as session:
            shot = Shot(
                project_id=project_id,
                order_index=0,
                duration_sec=6,
                tier="standard",
                prompt_text="Test prompt",
            )
            session.add(shot)
            await session.commit()
            shot_id = shot.id

            clip = BrollClip(
                shot_id=shot_id,
                project_id=project_id,
                status="done",
                clip_path="/tmp/fake.mp4",
                thumbnail_path="/tmp/fake.jpg",
                prompt_text="B-roll prompt",
                clip_meta={"location": "forest", "mood": "serene"},
            )
            session.add(clip)
            await session.commit()

        resp = await client.get(f"/api/scenes/{shot_id}/broll")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["status"] == "done"
        assert data[0]["metadata"]["location"] == "forest"

    @pytest.mark.asyncio
    async def test_broll_list_pagination(self, client: AsyncClient) -> None:
        """B-Roll list should honour skip and limit parameters."""
        create_resp = await client.post("/projects", json={"name": "Pagination Broll Test"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

        from backend.models.project import Shot, BrollClip
        async with AsyncSessionLocal() as session:
            shot = Shot(
                project_id=project_id,
                order_index=0,
                duration_sec=6,
                tier="standard",
                prompt_text="Pagination prompt",
            )
            session.add(shot)
            await session.commit()
            shot_id = shot.id

            for i in range(5):
                clip = BrollClip(
                    shot_id=shot_id,
                    project_id=project_id,
                    status="done",
                    clip_path=f"/tmp/fake_{i}.mp4",
                    prompt_text=f"Clip {i}",
                )
                session.add(clip)
            await session.commit()

        resp = await client.get(f"/api/scenes/{shot_id}/broll?limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

        resp = await client.get(f"/api/scenes/{shot_id}/broll?skip=2&limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

        resp = await client.get(f"/api/scenes/{shot_id}/broll?skip=4&limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

        resp = await client.get(f"/api/scenes/{shot_id}/broll?skip=10&limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_download_broll(self, client: AsyncClient) -> None:
        create_resp = await client.post("/projects", json={"name": "Download Broll Test"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

        from backend.models.project import Shot, BrollClip
        async with AsyncSessionLocal() as session:
            shot = Shot(
                project_id=project_id,
                order_index=0,
                duration_sec=6,
                tier="standard",
                prompt_text="Test prompt",
            )
            session.add(shot)
            await session.commit()
            shot_id = shot.id

            # Create a real temp file
            tmp_clip = Path("/tmp/test_broll_download.mp4")
            tmp_clip.write_bytes(b"fake mp4 data")

            clip = BrollClip(
                shot_id=shot_id,
                project_id=project_id,
                status="done",
                clip_path=str(tmp_clip),
            )
            session.add(clip)
            await session.commit()
            clip_id = clip.id

        resp = await client.get(f"/api/broll/{clip_id}/download")
        assert resp.status_code == 200
        assert resp.content == b"fake mp4 data"
        tmp_clip.unlink(missing_ok=True)


class TestGenerateAllBroll:
    @pytest.mark.asyncio
    async def test_bulk_generation(self, client: AsyncClient) -> None:
        create_resp = await client.post("/projects", json={"name": "Bulk Broll Test"})
        assert create_resp.status_code == 200
        project_id = create_resp.json()["id"]

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

        with patch("backend.app.MPTBrollBridge.generate_for_shot", return_value={
            "clip_path": "/tmp/fake_broll.mp4",
            "thumbnail_path": "/tmp/fake_broll.jpg",
            "metadata": {},
            "cost_usd": 0.0,
            "provider_id": "mpt",
            "prompt_text": "B-roll prompt",
            "duration_sec": 4.0,
        }):
            resp = await client.post(f"/api/projects/{project_id}/generate-all-broll")

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 3
        assert len(data["queued"]) == 3
