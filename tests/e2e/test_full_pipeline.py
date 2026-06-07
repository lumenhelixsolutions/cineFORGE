"""End-to-end Playwright test driving the full CineForge pipeline.

DoD #10: One Playwright E2E test drives the full pipeline against a mocked backend.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest
import requests
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


@pytest.mark.e2e
class TestFullPipeline:
    def test_full_pipeline(
        self,
        backend_server: str,
        frontend_page,
        mock_video_adapter,
        tmp_path: Path,
    ) -> None:
        page = frontend_page

        # ------------------------------------------------------------------
        # a. App is open and onboarding has been skipped via localStorage.
        # ------------------------------------------------------------------
        expect(page.locator("text=Projects")).to_be_visible(timeout=15000)

        # ------------------------------------------------------------------
        # b. Create a new project via the UI
        # ------------------------------------------------------------------
        page.on("dialog", lambda dialog: dialog.accept("E2E Test Project"))
        page.click("text=New")

        page.wait_for_url(lambda url: "/project/" in url, timeout=10000)
        project_id = page.url.split("/project/")[1].split("?")[0]

        # ------------------------------------------------------------------
        # c. Upload a simple text file as a source
        # ------------------------------------------------------------------
        page.click("text=Sources")
        test_file = tmp_path / "source.txt"
        test_file.write_text(
            "A woman discovers an old film reel in her grandmother's attic. "
            "The reel contains footage of a mysterious figure that seems to predict future events."
        )
        with page.expect_response(
            lambda resp: "/sources" in resp.url and resp.status == 200
        ):
            page.set_input_files('input[type="file"]', str(test_file))

        # Wait for the source to appear in the Sources panel
        expect(page.locator(".max-w-2xl >> text=txt")).to_be_visible(timeout=15000)
        expect(page.locator(".max-w-2xl >> text=words")).to_be_visible(timeout=15000)

        # ------------------------------------------------------------------
        # d. Generate treatment
        # ------------------------------------------------------------------
        page.click("text=Storyboard")
        with page.expect_response(
            lambda resp: "/treatment" in resp.url and resp.status == 200
        ):
            page.click("text=Generate Treatment")

        # Switch back to Sources to see the confirmation text
        page.click("text=Sources")
        expect(page.locator(".max-w-2xl >> text=Treatment generated")).to_be_visible(timeout=15000)

        # ------------------------------------------------------------------
        # e. Generate storyboard
        # ------------------------------------------------------------------
        page.click("text=Storyboard")
        page.click("text=Generate Storyboard")

        # ------------------------------------------------------------------
        # f. Verify shots appear in the Storyboard tab
        # ------------------------------------------------------------------
        expect(page.locator("text=#1")).to_be_visible(timeout=15000)
        expect(page.locator("text=#2")).to_be_visible(timeout=15000)

        # ------------------------------------------------------------------
        # g. Trigger render (mock adapter is already active)
        # ------------------------------------------------------------------
        page.click("text=Render")

        # ------------------------------------------------------------------
        # h. Poll backend until shot statuses change to done/failed, then verify UI
        # ------------------------------------------------------------------
        for _ in range(40):
            proj = requests.get(
                f"{backend_server}/projects/{project_id}", timeout=5
            ).json()
            if all(s["status"] in ("done", "failed") for s in proj.get("shots", [])):
                break
            time.sleep(0.5)
        else:
            pytest.fail("Render did not complete in time")

        # Refresh UI state
        page.reload()
        page.wait_for_load_state("networkidle")
        page.click("text=E2E Test Project")
        page.click("text=Storyboard")

        # Each rendered shot shows a <video> preview
        expect(page.locator("video")).to_have_count(2, timeout=15000)

        # ------------------------------------------------------------------
        # i. Trigger stitch
        # ------------------------------------------------------------------
        page.click("text=Stitch")
        expect(page.locator("text=Stitch complete")).to_be_visible(timeout=20000)

        # ------------------------------------------------------------------
        # j. Verify master.mp4 appears in the Preview tab
        # ------------------------------------------------------------------
        page.click("text=Preview")
        master_video = page.locator("video")
        expect(master_video).to_be_visible(timeout=15000)
        src = master_video.get_attribute("src")
        assert src is not None
        assert "master.mp4" in src
