"""Unit tests for lookBOOK living-panels review generation."""

from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from backend.app import app
from backend.ingest.living_review import build_review_html, build_review_payload


TREATMENT_WITH_CHOREOGRAPHY = {
    "title": "lookBOOK import",
    "source": "lookbook",
    "choreography": {
        "schema": "lookbook.choreography.v0.1",
        "lines": [
            {
                "line_index": 0,
                "speaker": "Hero",
                "text": "Hello from panel one.",
                "classification": "dialogue",
                "panel_index": 0,
                "words": ["Hello", "from", "panel", "one."],
            }
        ],
        "voice_cast": {"Hero": {"pitch": 1.0, "rate": 1.0}},
    },
    "panels": [{"panel_index": 0, "bbox": {"x": 0, "y": 0, "w": 200, "h": 300}}],
    "shot_graph": {
        "schema": "lookbook.shot_graph.v0.3",
        "shots": [{"shot_index": 0, "camera": "push in", "panels": [0]}],
    },
}


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


def test_build_review_payload_unavailable_without_choreography():
    payload = build_review_payload({"source": "lookbook"})
    assert payload["available"] is False
    assert "choreography" in payload["message"]


def test_build_review_payload_available_with_choreography():
    payload = build_review_payload(TREATMENT_WITH_CHOREOGRAPHY, project_name="Demo")
    assert payload["available"] is True
    assert payload["title"] == "Demo"
    assert payload["choreography"]["lines"][0]["speaker"] == "Hero"
    assert payload["panels"][0]["panel_index"] == 0


def test_build_review_html_contains_living_panels_stage():
    html_doc = build_review_html(TREATMENT_WITH_CHOREOGRAPHY, project_name="Demo")
    assert "living panels" in html_doc.lower()
    assert "lookbook-data" in html_doc
    assert "Hello from panel one." in html_doc


def test_build_review_html_empty_state():
    html_doc = build_review_html({"source": "lookbook"})
    assert "living panels" in html_doc.lower()
    assert "choreography" in html_doc.lower()


class TestLookbookReviewEndpoint:
    @pytest.mark.asyncio
    async def test_returns_404_for_missing_project(self, client: AsyncClient) -> None:
        resp = await client.get("/projects/nonexistent/lookbook/review?format=json")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_json_unavailable_without_choreography(self, client: AsyncClient) -> None:
        create_resp = await client.post("/projects", json={"name": "No Choreo"})
        project_id = create_resp.json()["id"]

        resp = await client.get(f"/projects/{project_id}/lookbook/review?format=json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["available"] is False

    @pytest.mark.asyncio
    async def test_json_and_html_available_after_lookbook_ingest(self, client: AsyncClient) -> None:
        create_resp = await client.post("/projects", json={"name": "Living Review"})
        project_id = create_resp.json()["id"]

        ingest_resp = await client.post(
            f"/projects/{project_id}/ingest/lookbook",
            json={
                "shot_graph": TREATMENT_WITH_CHOREOGRAPHY["shot_graph"],
                "choreography": TREATMENT_WITH_CHOREOGRAPHY["choreography"],
                "panels": TREATMENT_WITH_CHOREOGRAPHY["panels"],
            },
        )
        assert ingest_resp.status_code == 200

        json_resp = await client.get(f"/projects/{project_id}/lookbook/review?format=json")
        assert json_resp.status_code == 200
        assert json_resp.json()["available"] is True

        html_resp = await client.get(f"/projects/{project_id}/lookbook/review?format=html")
        assert html_resp.status_code == 200
        assert "text/html" in html_resp.headers.get("content-type", "")
        assert "Hello from panel one." in html_resp.text