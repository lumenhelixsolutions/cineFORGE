"""Playwright pytest configuration and fixtures for CineForge E2E tests."""
from __future__ import annotations

import http.server
import os
import socket
import socketserver
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Generator

import pytest

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_server(url: str, timeout: float = 30.0) -> None:
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"Server at {url} did not start within {timeout}s")


# ---------------------------------------------------------------------------
# Backend fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def backend_server() -> Generator[str, None, None]:
    """Start the FastAPI backend on a random port and yield its base URL."""
    port = _free_port()
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    data_dir = tempfile.mkdtemp(prefix="cineforge_e2e_")

    # Set environment variables *before* importing backend.app so that
    # settings, database, etc. pick them up.
    env_overrides = {
        "CINEFORGE_PORT": str(port),
        "CINEFORGE_HOST": "127.0.0.1",
        "CINEFORGE_DATA_DIR": data_dir,
        "CINEFORGE_DATABASE_URL": f"sqlite+aiosqlite:///{db_path}",
        "CINEFORGE_MOCK_VIDEO": "true",
    }
    old_env = os.environ.copy()
    os.environ.update(env_overrides)

    # Save the original backend modules so we can restore them later.
    original_backend_modules = {
        k: sys.modules[k] for k in list(sys.modules) if k.startswith("backend.")
    }

    # Purge any previously imported backend modules so we get a clean state.
    mods_to_remove = [k for k in sys.modules if k.startswith("backend.")]
    for mod in mods_to_remove:
        del sys.modules[mod]

    import backend.app as app_module

    # Restore original environment so we don't leak into other tests.
    os.environ.clear()
    os.environ.update(old_env)

    server_holder: list[Any] = []

    def _run() -> None:
        import uvicorn

        config = uvicorn.Config(
            app_module.app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
            reload=False,
        )
        server = uvicorn.Server(config)
        server_holder.append(server)
        server.run()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    # Wait until the server instance is available.
    while not server_holder:
        time.sleep(0.05)

    try:
        _wait_for_server(f"http://127.0.0.1:{port}/health")
        yield f"http://127.0.0.1:{port}"
    finally:
        server_holder[0].should_exit = True
        thread.join(timeout=5)
        import shutil

        shutil.rmtree(data_dir, ignore_errors=True)
        Path(db_path).unlink(missing_ok=True)

        # Restore original backend modules so that subsequent tests get a
        # fresh, unmodified import state.
        for k in list(sys.modules):
            if k.startswith("backend."):
                del sys.modules[k]
        sys.modules.update(original_backend_modules)


# ---------------------------------------------------------------------------
# Frontend static server fixture
# ---------------------------------------------------------------------------

class _SPAHandler(http.server.SimpleHTTPRequestHandler):
    """Serve ``ui/dist`` and fall back to ``index.html`` for SPA routes."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        directory = str(Path(__file__).parent.parent.parent / "ui" / "dist")
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def do_GET(self) -> None:
        path = self.translate_path(self.path)
        if Path(path).is_file():
            super().do_GET()
        else:
            self.path = "/index.html"
            super().do_GET()


class _ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


@pytest.fixture(scope="module")
def frontend_server() -> Generator[str, None, None]:
    """Serve the built SolidJS frontend on a random port."""
    port = _free_port()
    server = _ReusableTCPServer(("127.0.0.1", port), _SPAHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()


# ---------------------------------------------------------------------------
# Mock adapter fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_video_adapter(
    backend_server: str, monkeypatch: pytest.MonkeyPatch
) -> Generator[Any, None, None]:
    """Patch the backend adapter registry with mock video and LLM adapters."""
    import asyncio

    import backend.app
    from backend.adapters.protocols import (
        CapabilityError,
        ExtendRequest,
        LLMCapabilities,
        LLMRequest,
        LLMResponse,
        LLMUsage,
        VideoCapabilities,
        VideoGenRequest,
        VideoGenResult,
    )

    class MockVideoAdapter:
        capabilities = VideoCapabilities(
            provider_id="mock.video",
            display_name="Mock Video",
            supported_durations_sec=[4, 6, 8],
            supported_aspect_ratios=["16:9", "9:16", "1:1"],
            supported_resolutions=["720p", "1080p"],
            max_reference_images=0,
            supports_native_audio=False,
            supports_frame_conditioning=False,
            supports_extend=False,
            max_extend_total_sec=None,
            supports_negative_prompt=False,
            is_local=True,
            cost_per_second_usd=0.0,
            notes="mock",
        )

        async def generate(self, req: VideoGenRequest) -> VideoGenResult:
            await asyncio.sleep(0.5)
            out = Path(tempfile.mktemp(suffix=".mp4"))
            from tests.e2e.test_video import generate_test_mp4

            generate_test_mp4(out, duration_sec=req.duration_sec)
            return VideoGenResult(
                clip_path=out,
                last_frame_path=out,
                duration_sec=float(req.duration_sec),
                has_audio=False,
                cost_usd=0.0,
                provider_id=self.capabilities.provider_id,
            )

        async def extend(self, req: ExtendRequest) -> VideoGenResult:
            raise CapabilityError("Extend not supported")

        async def healthcheck(self) -> bool:
            return True

    mock_video = MockVideoAdapter()

    class MockLLMDirector:
        capabilities = LLMCapabilities(
            provider_id="mock.llm",
            display_name="Mock LLM",
            context_window=128_000,
            supports_prompt_caching=False,
            supports_structured_output=True,
            supports_tool_use=False,
            is_local=True,
            cost_per_1k_input_usd=0.0,
            cost_per_1k_output_usd=0.0,
            cost_per_1k_cached_input_usd=0.0,
        )

        async def complete(self, req: LLMRequest) -> LLMResponse:
            content: Any
            schema = req.response_schema
            if schema and isinstance(schema, dict):
                props = schema.get("properties", {})
                if "acts" in props:
                    content = {
                        "logline": "A woman discovers an old film reel.",
                        "theme": "memory",
                        "tone": "nostalgic",
                        "acts": [
                            {
                                "title": "Act 1",
                                "beats": [
                                    {
                                        "id": "b1",
                                        "summary": "Discovery",
                                        "target_duration_sec": 6,
                                        "emotional_register": "wonder",
                                    }
                                ],
                            },
                            {
                                "title": "Act 2",
                                "beats": [
                                    {
                                        "id": "b2",
                                        "summary": "Mystery",
                                        "target_duration_sec": 6,
                                        "emotional_register": "tense",
                                    }
                                ],
                            },
                            {
                                "title": "Act 3",
                                "beats": [
                                    {
                                        "id": "b3",
                                        "summary": "Resolution",
                                        "target_duration_sec": 6,
                                        "emotional_register": "triumph",
                                    }
                                ],
                            },
                        ],
                        "style_pack_suggestion": "cinematic_noir",
                    }
                elif "items" in schema:
                    content = [
                        {
                            "id": "s1",
                            "order_index": 0,
                            "duration_sec": 6,
                            "tier": "hero",
                            "summary": "Opening shot",
                            "continuity": {},
                            "bridge_strategy": "hard_cut",
                            "preferred_bridge": "hard_cut",
                            "camera": "wide",
                            "lighting": "natural",
                            "audio_hint": "ambient",
                        },
                        {
                            "id": "s2",
                            "order_index": 1,
                            "duration_sec": 6,
                            "tier": "standard",
                            "summary": "Reveal",
                            "continuity": {},
                            "bridge_strategy": "hard_cut",
                            "preferred_bridge": "hard_cut",
                            "camera": "medium",
                            "lighting": "soft",
                            "audio_hint": "music",
                        },
                    ]
                else:
                    content = "mock response"
            else:
                content = "mock response"

            return LLMResponse(
                content=content,
                usage=LLMUsage(
                    input_tokens=10,
                    output_tokens=10,
                    cached_input_tokens=0,
                    cost_usd=0.0,
                ),
                provider_id=self.capabilities.provider_id,
            )

        async def healthcheck(self) -> bool:
            return True

    mock_llm = MockLLMDirector()

    # Patch registry accessors so any resolved name returns our mocks.
    monkeypatch.setattr(
        backend.app.app_ctx.registry,
        "video_adapter",
        lambda name: mock_video,
    )
    monkeypatch.setattr(
        backend.app.app_ctx.registry,
        "llm_adapter",
        lambda name: mock_llm,
    )
    # Also pin the router so it resolves to names we control.
    monkeypatch.setattr(
        backend.app.app_ctx.router,
        "resolve_video",
        lambda tier, profile, preview=False: "mock.video",
    )
    monkeypatch.setattr(
        backend.app.app_ctx.router,
        "resolve_llm",
        lambda task, profile: "mock.llm",
    )

    yield mock_video


# ---------------------------------------------------------------------------
# Playwright page fixture navigated to the app
# ---------------------------------------------------------------------------

@pytest.fixture
def frontend_page(
    page: Any,
    backend_server: str,
    frontend_server: str,
) -> Generator[Any, None, None]:
    """Return a Playwright page navigated to the CineForge frontend.

    Requests to the hard-coded backend port (8765) are transparently
    rewritten to the dynamic *backend_server* port.
    """

    def _handle_route(route: Any, request: Any) -> None:
        if request.url.startswith("http://127.0.0.1:8765/"):
            new_url = request.url.replace(
                "http://127.0.0.1:8765/", f"{backend_server}/"
            )
            route.continue_(url=new_url)
        else:
            route.continue_()

    page.route("http://127.0.0.1:8765/**", _handle_route)

    # Skip the onboarding wizard.
    page.context.add_init_script(
        "localStorage.setItem('cineforge_onboarding_done', 'true');"
    )

    page.goto(frontend_server)
    page.wait_for_selector("text=Projects", timeout=15000)
    yield page
