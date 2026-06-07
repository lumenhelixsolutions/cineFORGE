"""CineForge — Pre-flight checks before render jobs."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from backend.models.project import Project


class PreflightError(Exception):
    """Raised when a pre-flight check fails."""

    pass


def check_disk_space(project: Project, required_mb: int = 5120) -> dict[str, Any]:
    """Ensure enough disk space exists for a render job.

    Args:
        project: The project being rendered.
        required_mb: Minimum free space in megabytes (default 5GB).

    Returns:
        Status dict with free space info.

    Raises:
        PreflightError: If insufficient disk space.
    """
    output_dir = (
        Path(project.output_dir)
        if hasattr(project, "output_dir")
        else Path.home() / ".cineforge" / "projects" / str(project.id)
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    usage = shutil.disk_usage(output_dir)
    free_mb = usage.free // (1024 * 1024)
    required_bytes = required_mb * 1024 * 1024

    if usage.free < required_bytes:
        raise PreflightError(
            f"Insufficient disk space: {free_mb:,} MB free, {required_mb:,} MB required for project {project.id}"
        )

    return {
        "check": "disk_space",
        "status": "ok",
        "free_mb": free_mb,
        "required_mb": required_mb,
    }


def run_all(project: Project) -> list[dict[str, Any]]:
    """Run all pre-flight checks."""
    results: list[dict[str, Any]] = []
    results.append(check_disk_space(project))
    return results
