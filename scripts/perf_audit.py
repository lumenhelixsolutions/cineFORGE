"""Performance audit script for CineForge.

Measures:
- Backend cold-start time
- UI build time
- Tauri bundle size
- Memory usage during mocked 5-shot render
- SQLite query times for project load

Outputs JSON report to perf_report.json.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any

REPORT_PATH = Path("perf_report.json")


def _run(
    cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )


def audit_backend_cold_start() -> dict[str, Any]:
    """Time until health endpoint responds."""
    env = {
        **dict(os.environ),
        "CINEFORGE_MOCK_VIDEO": "true",
        "CINEFORGE_MOCK_LLM": "true",
        "CINEFORGE_PORT": "9877",
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "backend.app"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    start = time.perf_counter()
    ok = False
    error = ""
    try:
        import urllib.request

        for _ in range(30):
            try:
                urllib.request.urlopen("http://127.0.0.1:9877/health", timeout=2)
                ok = True
                break
            except Exception as exc:
                error = str(exc)
                time.sleep(0.5)
    finally:
        proc.terminate()
        proc.wait(timeout=10)
    elapsed = time.perf_counter() - start
    return {
        "metric": "backend_cold_start_sec",
        "value": round(elapsed, 2),
        "ok": ok,
        "error": "" if ok else error,
    }


def audit_ui_build_time() -> dict[str, Any]:
    """Time to run `npm run build` in ui/."""
    ui_dir = Path("ui")
    if not (ui_dir / "node_modules").exists():
        return {"metric": "ui_build_sec", "value": None, "ok": False, "error": "node_modules missing"}
    start = time.perf_counter()
    result = _run(["npm", "run", "build"], cwd=ui_dir)
    elapsed = time.perf_counter() - start
    return {
        "metric": "ui_build_sec",
        "value": round(elapsed, 2),
        "ok": result.returncode == 0,
        "error": result.stderr[:500] if result.returncode != 0 else "",
    }


def audit_tauri_bundle_size() -> dict[str, Any]:
    """Find built Tauri bundles and report sizes in MB."""
    bundle_dir = Path("src-tauri/target/release/bundle")
    sizes: dict[str, float] = {}
    if bundle_dir.exists():
        for f in bundle_dir.rglob("*"):
            if f.is_file():
                sizes[str(f.relative_to(bundle_dir)).replace("\\", "/")] = round(f.stat().st_size / (1024 * 1024), 2)
    return {
        "metric": "tauri_bundle_sizes_mb",
        "value": sizes,
        "ok": bool(sizes),
        "error": "" if sizes else "No bundles found; run cargo tauri build first",
    }


def audit_mock_render_memory() -> dict[str, Any]:
    """Memory usage during a mocked 5-shot render pipeline."""
    try:
        from backend.adapters.registry import get_registry
        from backend.generator.pipeline import RenderPipeline
        from backend.token_ledger.router import RoutingConfig
        from backend.models.project import Project, Shot
    except Exception as exc:
        return {"metric": "mock_render_memory_mb", "value": None, "ok": False, "error": str(exc)}

    registry = get_registry()
    router = RoutingConfig.from_file(Path.home() / ".cineforge" / "routing.yaml")
    if not router.config:
        # fallback empty config
        router.config = {"profiles": {"hybrid": {}}}
        router.profiles = {"hybrid": {"video": {}, "llm": {}}}

    proj_dir = Path(".pytest_tmp/perf_audit_project")
    proj_dir.mkdir(parents=True, exist_ok=True)

    pipeline = RenderPipeline(registry=registry, router=router, project_dir=proj_dir)

    # Create mock project and shots
    project = Project(
        id="perf-proj",
        name="Perf",
        aspect_ratio="16:9",
        resolution="1080p",
        routing_profile="hybrid",
        preview_mode=True,
    )
    shots = [
        Shot(
            id=f"s{i}",
            project_id="perf-proj",
            order_index=i,
            duration_sec=6,
            tier="standard",
            prompt_text="test",
            status="draft",
        )
        for i in range(5)
    ]

    tracemalloc.start()
    start = time.perf_counter()
    try:
        import asyncio

        async def _run_all() -> None:
            for shot in shots:
                try:
                    await pipeline.render_shot(shot=shot, project=project)
                except Exception:
                    pass  # mock adapters may still fail; we only care about memory

        asyncio.get_event_loop().run_until_complete(_run_all())
    except Exception as exc:
        return {"metric": "mock_render_memory_mb", "value": None, "ok": False, "error": str(exc)}
    finally:
        elapsed = time.perf_counter() - start
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    return {
        "metric": "mock_render_memory_mb",
        "value": {
            "current_mb": round(current / (1024 * 1024), 2),
            "peak_mb": round(peak / (1024 * 1024), 2),
            "elapsed_sec": round(elapsed, 2),
        },
        "ok": True,
        "error": "",
    }


def audit_sqlite_query_times() -> dict[str, Any]:
    """Time simple project load queries."""
    try:
        from backend.database import AsyncSessionLocal
        from backend.models.project import Project
        from sqlalchemy import select
        import asyncio
    except Exception as exc:
        return {"metric": "sqlite_query_ms", "value": None, "ok": False, "error": str(exc)}

    async def _measure() -> dict[str, Any]:
        times: list[float] = []
        async with AsyncSessionLocal() as db:
            for _ in range(5):
                start = time.perf_counter()
                await db.execute(select(Project).limit(1))
                times.append((time.perf_counter() - start) * 1000)
        return {
            "metric": "sqlite_query_ms",
            "value": {
                "avg_ms": round(sum(times) / len(times), 2),
                "min_ms": round(min(times), 2),
                "max_ms": round(max(times), 2),
            },
            "ok": True,
            "error": "",
        }

    try:
        return asyncio.get_event_loop().run_until_complete(_measure())
    except Exception as exc:
        return {"metric": "sqlite_query_ms", "value": None, "ok": False, "error": str(exc)}


def main() -> None:
    results: list[dict[str, Any]] = []
    results.append(audit_backend_cold_start())
    results.append(audit_ui_build_time())
    results.append(audit_tauri_bundle_size())
    results.append(audit_mock_render_memory())
    results.append(audit_sqlite_query_times())

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "results": results,
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Report written to {REPORT_PATH}")
    for r in results:
        status = "OK" if r["ok"] else "FAIL"
        print(f"  [{status}] {r['metric']}: {r['value']}")


if __name__ == "__main__":
    main()
