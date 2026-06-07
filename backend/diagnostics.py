"""Built-in diagnostic system for CineForge setup and onboarding.

Checks every critical component and reports actionable fixes.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class DiagnosticResult:
    """Single diagnostic check result."""

    def __init__(self, name: str, status: str, message: str, fix: str = "") -> None:
        self.name = name
        self.status = status  # "ok", "warning", "error"
        self.message = message
        self.fix = fix

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "fix": self.fix,
        }


class DiagnosticsEngine:
    """Runs comprehensive system diagnostics."""

    def __init__(self, data_dir: Path, projects_dir: Path) -> None:
        self.data_dir = data_dir
        self.projects_dir = projects_dir

    async def run_all(self) -> list[DiagnosticResult]:
        """Run all diagnostic checks."""
        results: list[DiagnosticResult] = []
        results.append(self._check_backend_health())
        results.append(self._check_cors())
        results.append(self._check_python_version())
        results.append(self._check_ffmpeg())
        results.append(await self._check_adapters())
        results.append(self._check_env_file())
        results.append(self._check_gpu())
        results.append(self._check_data_dir())
        results.append(self._check_database())
        results.append(self._check_frontend_deps())
        return results

    def _check_backend_health(self) -> DiagnosticResult:
        """Verify the backend process is responding."""
        try:
            import urllib.request

            with urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=2) as resp:
                data = resp.read()
                if b"ok" in data:
                    return DiagnosticResult("Backend Health", "ok", "Backend responding on port 8765")
                return DiagnosticResult("Backend Health", "warning", "Backend responded but status unclear")
        except Exception as exc:
            return DiagnosticResult(
                "Backend Health", "error", f"Backend not reachable: {exc}", "Run: python -m backend.app"
            )

    def _check_cors(self) -> DiagnosticResult:
        """Verify CORS headers are present on responses."""
        try:
            import urllib.request

            req = urllib.request.Request(
                "http://127.0.0.1:8765/health", headers={"Origin": "http://localhost:5173"}, method="GET"
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                cors = resp.headers.get("Access-Control-Allow-Origin", "")
                if cors == "*" or "localhost:5173" in cors:
                    return DiagnosticResult("CORS", "ok", f"CORS enabled: {cors}")
                return DiagnosticResult(
                    "CORS",
                    "warning",
                    f"CORS header missing or incorrect: '{cors}'",
                    "Restart backend after code changes",
                )
        except Exception as exc:
            return DiagnosticResult("CORS", "error", f"Cannot test CORS: {exc}", "Ensure backend is running")

    def _check_python_version(self) -> DiagnosticResult:
        """Check Python is 3.12+."""
        import sys

        version = sys.version_info
        if version.major == 3 and version.minor >= 12:
            return DiagnosticResult("Python Version", "ok", f"Python {version.major}.{version.minor}.{version.micro}")
        return DiagnosticResult(
            "Python Version",
            "error",
            f"Python {version.major}.{version.minor} found, 3.12+ required",
            "Install Python 3.12 from python.org",
        )

    def _check_ffmpeg(self) -> DiagnosticResult:
        """Check FFmpeg binary is in PATH."""
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version_line = result.stdout.splitlines()[0]
                return DiagnosticResult("FFmpeg", "ok", version_line[:60])
            return DiagnosticResult("FFmpeg", "error", "ffmpeg returned non-zero", "Install FFmpeg and add to PATH")
        except FileNotFoundError:
            return DiagnosticResult(
                "FFmpeg",
                "error",
                "ffmpeg not found in PATH",
                "Install: winget install Gyan.FFmpeg  (or brew install ffmpeg on macOS)",
            )
        except Exception as exc:
            return DiagnosticResult("FFmpeg", "error", str(exc), "Check FFmpeg installation")

    async def _check_adapters(self) -> DiagnosticResult:
        """Check how many adapters loaded successfully."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("http://127.0.0.1:8765/capabilities")
                data = resp.json()
                video = len(data.get("video", {}))
                llm = len(data.get("llm", {}))
                embedder = len(data.get("embedder", {}))
                total = video + llm + embedder
                if total >= 3:
                    return DiagnosticResult(
                        "Adapters", "ok", f"{video} video, {llm} LLM, {embedder} embedder adapters loaded"
                    )
                return DiagnosticResult(
                    "Adapters",
                    "warning",
                    f"Only {total} adapters loaded ({video} video, {llm} LLM, {embedder} embedder)",
                    "Run: pip install -e .",
                )
        except Exception as exc:
            return DiagnosticResult(
                "Adapters",
                "error",
                f"Cannot query adapters: {exc}",
                "Ensure backend is running and entry points are correct",
            )

    def _check_env_file(self) -> DiagnosticResult:
        """Check if .env file exists and has required keys."""
        env_path = Path(".env")
        if not env_path.exists():
            return DiagnosticResult(
                "Environment Config", "warning", "No .env file found", "Copy .env.example to .env and add your API keys"
            )
        content = env_path.read_text()
        has_anthropic = "ANTHROPIC_API_KEY" in content and "your-" not in content
        has_google = "GOOGLE_CLOUD_PROJECT" in content and "your-" not in content
        mock_mode = "CINEFORGE_MOCK_VIDEO=true" in content or "CINEFORGE_MOCK_LLM=true" in content
        if mock_mode:
            return DiagnosticResult("Environment Config", "ok", "Mock mode enabled (zero-cost testing)")
        if has_anthropic or has_google:
            return DiagnosticResult("Environment Config", "ok", "API keys configured")
        return DiagnosticResult(
            "Environment Config",
            "warning",
            ".env exists but no valid API keys found",
            "Add ANTHROPIC_API_KEY or GOOGLE_CLOUD_PROJECT, or enable mock mode",
        )

    def _check_gpu(self) -> DiagnosticResult:
        """Check for CUDA GPU availability."""
        try:
            import torch

            if torch.cuda.is_available():
                name = torch.cuda.get_device_name(0)
                mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
                return DiagnosticResult("GPU", "ok", f"{name} ({mem:.1f} GB VRAM)")
            return DiagnosticResult(
                "GPU",
                "warning",
                "No CUDA GPU detected. CPU-only mode for LLM, video generation requires GPU.",
                "Install NVIDIA drivers and CUDA toolkit, or use cloud profiles",
            )
        except ImportError:
            return DiagnosticResult(
                "GPU", "warning", "PyTorch not installed — cannot detect GPU", "Run: pip install torch"
            )
        except Exception as exc:
            return DiagnosticResult("GPU", "warning", str(exc), "Check NVIDIA driver installation")

    def _check_data_dir(self) -> DiagnosticResult:
        """Check data directory exists and is writable."""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            test_file = self.data_dir / ".write_test"
            test_file.write_text("ok")
            test_file.unlink()
            return DiagnosticResult("Data Directory", "ok", f"{self.data_dir} is writable")
        except Exception as exc:
            return DiagnosticResult(
                "Data Directory",
                "error",
                f"Cannot write to {self.data_dir}: {exc}",
                "Check permissions or set CINEFORGE_DATA_DIR to a writable path",
            )

    def _check_database(self) -> DiagnosticResult:
        """Check SQLite database is accessible."""
        try:
            from sqlalchemy import create_engine, text

            db_url = os.getenv("CINEFORGE_DATABASE_URL", f"sqlite:///{self.data_dir / 'cineforge.db'}")
            engine = create_engine(db_url.replace("+aiosqlite", ""))
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return DiagnosticResult("Database", "ok", "SQLite database accessible")
        except Exception as exc:
            return DiagnosticResult(
                "Database", "error", f"Database error: {exc}", "Delete cineforge.db and restart to recreate"
            )

    def _check_frontend_deps(self) -> DiagnosticResult:
        """Check if UI node_modules exists."""
        ui_dir = Path("ui")
        node_modules = ui_dir / "node_modules"
        if node_modules.exists():
            return DiagnosticResult("Frontend Dependencies", "ok", "node_modules present")
        return DiagnosticResult("Frontend Dependencies", "error", "node_modules not found", "Run: cd ui && npm install")
