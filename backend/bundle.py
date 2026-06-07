"""Project bundle export/import (.cineforge files).

A .cineforge bundle is a ZIP containing:
  - manifest.json   (schema version, project metadata, DB rows)
  - media/          (project media files)
"""
from __future__ import annotations

import json
import shutil
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.project import Project, Shot, SourceDoc, Treatment, RenderJob
from backend.settings import get_settings

BUNDLE_SCHEMA_VERSION = "1.0"


async def export_project_bundle(project_id: str, db: AsyncSession) -> Path:
    """Export a project and its media into a .cineforge bundle."""
    settings = get_settings()
    proj_dir = settings.projects_dir / project_id
    if not proj_dir.exists():
        raise FileNotFoundError(f"Project directory not found: {proj_dir}")

    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    proj = result.scalar_one_or_none()
    if proj is None:
        raise ValueError(f"Project not found: {project_id}")

    # Gather related rows
    shots = [
        {
            "id": s.id,
            "order_index": s.order_index,
            "duration_sec": s.duration_sec,
            "tier": s.tier,
            "continuity": s.continuity,
            "prompt_text": s.prompt_text,
            "prompt_hash": s.prompt_hash,
            "ref_image_paths": s.ref_image_paths,
            "bridge_strategy": s.bridge_strategy,
            "preferred_bridge": s.preferred_bridge,
            "clip_path": s.clip_path,
            "last_frame_path": s.last_frame_path,
            "status": s.status,
            "error": s.error,
            "cost_usd": s.cost_usd,
            "provider_id": s.provider_id,
            "render_started_at": s.render_started_at.isoformat() if s.render_started_at else None,
            "render_finished_at": s.render_finished_at.isoformat() if s.render_finished_at else None,
        }
        for s in proj.shots
    ]
    sources = [
        {
            "id": s.id,
            "kind": s.kind,
            "raw_path": s.raw_path,
            "normalized_path": s.normalized_path,
            "embedding_id": s.embedding_id,
            "extracted_text": s.extracted_text,
            "word_count": s.word_count,
        }
        for s in proj.sources
    ]
    treatments = [
        {
            "id": t.id,
            "json": t.json,
            "llm_model": t.llm_model,
            "token_usage": t.token_usage,
            "created_at": t.created_at.isoformat(),
        }
        for t in proj.treatments
    ]
    renders = [
        {
            "id": r.id,
            "started_at": r.started_at.isoformat(),
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "output_path": r.output_path,
            "timeline_json": r.timeline_json,
            "status": r.status,
            "error": r.error,
            "total_cost_usd": r.total_cost_usd,
        }
        for r in proj.renders
    ]

    manifest: dict[str, Any] = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "exported_at": datetime.utcnow().isoformat(),
        "project": {
            "id": proj.id,
            "name": proj.name,
            "created_at": proj.created_at.isoformat(),
            "updated_at": proj.updated_at.isoformat() if proj.updated_at else None,
            "style_pack_id": proj.style_pack_id,
            "aspect_ratio": proj.aspect_ratio,
            "resolution": proj.resolution,
            "target_duration_sec": proj.target_duration_sec,
            "preview_mode": proj.preview_mode,
            "routing_profile": proj.routing_profile,
            "budget_usd": proj.budget_usd,
            "tokens_used_input": proj.tokens_used_input,
            "tokens_used_output": proj.tokens_used_output,
            "tokens_used_cached": proj.tokens_used_cached,
        },
        "shots": shots,
        "sources": sources,
        "treatments": treatments,
        "renders": renders,
    }

    bundle_path = settings.projects_dir / f"{project_id}.cineforge"
    with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        for file_path in proj_dir.rglob("*"):
            if file_path.is_file():
                arcname = "media/" + str(file_path.relative_to(proj_dir)).replace("\\", "/")
                zf.write(file_path, arcname)

    return bundle_path


async def import_project_bundle(zip_path: Path, db: AsyncSession) -> Project:
    """Import a .cineforge bundle, inserting rows and copying media."""
    if not zip_path.exists():
        raise FileNotFoundError(f"Bundle not found: {zip_path}")

    with zipfile.ZipFile(zip_path, "r") as zf:
        try:
            manifest_data = json.loads(zf.read("manifest.json"))
        except KeyError:
            raise ValueError("Invalid bundle: manifest.json missing")

    if manifest_data.get("schema_version") != BUNDLE_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported bundle schema: {manifest_data.get('schema_version')}"
        )

    settings = get_settings()
    pm = manifest_data["project"]
    new_id = str(uuid.uuid4())
    new_proj_dir = settings.projects_dir / new_id
    new_proj_dir.mkdir(parents=True, exist_ok=True)

    # Copy media
    with zipfile.ZipFile(zip_path, "r") as zf:
        for item in zf.namelist():
            if item.startswith("media/"):
                dest = new_proj_dir / item[len("media/"):]
                dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(item) as src, open(dest, "wb") as dst:
                    shutil.copyfileobj(src, dst)

    # Create project
    proj = Project(
        id=new_id,
        name=pm.get("name", "Imported Project"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        style_pack_id=pm.get("style_pack_id"),
        aspect_ratio=pm.get("aspect_ratio", "16:9"),
        resolution=pm.get("resolution", "1080p"),
        target_duration_sec=pm.get("target_duration_sec", 60),
        preview_mode=pm.get("preview_mode", False),
        routing_profile=pm.get("routing_profile", "hybrid"),
        budget_usd=pm.get("budget_usd", 1.0),
        tokens_used_input=pm.get("tokens_used_input", 0),
        tokens_used_output=pm.get("tokens_used_output", 0),
        tokens_used_cached=pm.get("tokens_used_cached", 0),
    )
    db.add(proj)
    await db.flush()

    # Helper to rewrite paths
    def _rewrite(path: str | None) -> str | None:
        if not path:
            return None
        old_proj_id = pm["id"]
        return path.replace(str(settings.projects_dir / old_proj_id), str(new_proj_dir))

    # Insert shots
    for s in manifest_data.get("shots", []):
        shot = Shot(
            id=str(uuid.uuid4()),
            project_id=new_id,
            order_index=s["order_index"],
            duration_sec=s["duration_sec"],
            tier=s.get("tier", "standard"),
            continuity=s.get("continuity", {}),
            prompt_text=s.get("prompt_text", ""),
            prompt_hash=s.get("prompt_hash", ""),
            ref_image_paths=s.get("ref_image_paths", []),
            bridge_strategy=s.get("bridge_strategy", "hard_cut"),
            preferred_bridge=s.get("preferred_bridge", "hard_cut"),
            clip_path=_rewrite(s.get("clip_path")),
            last_frame_path=_rewrite(s.get("last_frame_path")),
            status=s.get("status", "draft"),
            error=s.get("error"),
            cost_usd=s.get("cost_usd", 0.0),
            provider_id=s.get("provider_id"),
            render_started_at=datetime.fromisoformat(s["render_started_at"]) if s.get("render_started_at") else None,
            render_finished_at=datetime.fromisoformat(s["render_finished_at"]) if s.get("render_finished_at") else None,
        )
        db.add(shot)

    # Insert sources
    for s in manifest_data.get("sources", []):
        source_doc = SourceDoc(
            id=str(uuid.uuid4()),
            project_id=new_id,
            kind=s["kind"],
            raw_path=_rewrite(s.get("raw_path")) or "",
            normalized_path=_rewrite(s.get("normalized_path")) or "",
            embedding_id=s.get("embedding_id"),
            extracted_text=s.get("extracted_text"),
            word_count=s.get("word_count", 0),
        )
        db.add(source_doc)

    # Insert treatments
    for t in manifest_data.get("treatments", []):
        treatment = Treatment(
            id=str(uuid.uuid4()),
            project_id=new_id,
            json=t.get("json", {}),
            llm_model=t.get("llm_model", ""),
            token_usage=t.get("token_usage", {}),
            created_at=datetime.fromisoformat(t["created_at"]) if t.get("created_at") else datetime.utcnow(),
        )
        db.add(treatment)

    # Insert render jobs
    for r in manifest_data.get("renders", []):
        job = RenderJob(
            id=str(uuid.uuid4()),
            project_id=new_id,
            started_at=datetime.fromisoformat(r["started_at"]) if r.get("started_at") else datetime.utcnow(),
            finished_at=datetime.fromisoformat(r["finished_at"]) if r.get("finished_at") else None,
            output_path=_rewrite(r.get("output_path")),
            timeline_json=r.get("timeline_json", {}),
            status=r.get("status", "done"),
            error=r.get("error"),
            total_cost_usd=r.get("total_cost_usd", 0.0),
        )
        db.add(job)

    await db.commit()
    await db.refresh(proj)
    return proj
