"""FastAPI entry point for CineForge backend."""

from __future__ import annotations

import contextvars
import json
import logging
import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Awaitable, Callable

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.settings import get_settings
from backend.models.project import init_db, Project, Shot, SourceDoc, Treatment, RenderJob, BrollClip
from backend.adapters.registry import get_registry
from backend.adapters.protocols import CapabilityError
from backend.ingest.pipeline import ingest_document
from backend.director.treatment import generate_treatment
from backend.director.storyboard import generate_storyboard
from backend.promptforge.template import PromptForge
from backend.promptforge.continuity import ContinuityBible
from backend.generator.pipeline import RenderPipeline
from backend.generator.extend_pipeline import ExtendPipeline
from backend.stitcher.timeline import Stitcher
from backend.token_ledger.router import RoutingConfig
from backend.prefabs.loader import PrefabLoader
from backend.stackbuilder.engine import ProjectConstraints, StackBuilder
from backend.diagnostics import DiagnosticsEngine
from backend.preflight import PreflightError, run_all as run_preflight
from backend.database import get_db, AsyncSessionLocal
from backend.auth import APIKeyMiddleware
from backend.telemetry import session_summary
from backend.bundle import export_project_bundle, import_project_bundle
from backend.broll.mpt_bridge import MPTBrollBridge
from tools.shared.mpt_bridge import get_bridge

# ── Structured logging ──────────────────────────────────────────
correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="")


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        cid = getattr(record, "correlation_id", "") or correlation_id_var.get()
        if cid:
            log_obj["correlation_id"] = cid
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        setattr(record, "correlation_id", correlation_id_var.get())
        return True


def _setup_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    handler.addFilter(CorrelationIdFilter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


_setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()
init_db(settings.database_url.replace("+aiosqlite", ""))

prefab_loader = PrefabLoader(settings.prefabs_dir)
routing_config = RoutingConfig.from_file(settings.data_dir / "routing.yaml")


class AppContext:
    """Single in-memory application context."""

    def __init__(self) -> None:
        self.registry = get_registry()
        self.prefabs = prefab_loader
        self.router = routing_config
        self.projects: dict[str, Any] = {}  # lightweight in-mem cache


app_ctx = AppContext()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("CineForge backend starting on %s:%d", settings.host, settings.port)
    # Copy shipped prefabs to user dir on first run
    shipped = Path(__file__).parent / "prefabs" / "shipped"
    if shipped.exists():
        for sub in ("style_packs", "grammars", "transitions", "luts"):
            src = shipped / sub
            dst = settings.prefabs_dir / sub
            if not dst.exists() and src.exists():
                shutil.copytree(src, dst)
    yield
    logger.info("CineForge backend shutting down")


app = FastAPI(title="CineForge", version="0.1.0", lifespan=lifespan)

# CORS: allow all origins for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)

# Auth middleware (disabled when CINEFORGE_API_KEY is not set)
app.add_middleware(APIKeyMiddleware)


@app.middleware("http")
async def correlation_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    cid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    correlation_id_var.set(cid)
    request.state.correlation_id = cid
    response = await call_next(request)
    response.headers["X-Request-ID"] = cid
    return response


# ═══════════════════════════════════════════════════════════════
# Health & capabilities
# ═══════════════════════════════════════════════════════════════


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
    }


@app.get("/capabilities")
async def capabilities() -> dict[str, Any]:
    return app_ctx.registry.all_capabilities()


@app.post("/capabilities/reload")
async def reload_capabilities() -> dict[str, Any]:
    app_ctx.registry.reload()
    return {"status": "reloaded"}


# ═══════════════════════════════════════════════════════════════
# Projects
# ═══════════════════════════════════════════════════════════════


class CreateProjectRequest(BaseModel):
    name: str
    aspect_ratio: str = "16:9"
    resolution: str = "1080p"
    target_duration_sec: int = 60
    style_pack_id: str | None = None
    routing_profile: str = settings.default_routing_profile


@app.post("/projects")
async def create_project(
    req: CreateProjectRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    proj = Project(
        name=req.name,
        aspect_ratio=req.aspect_ratio,
        resolution=req.resolution,
        target_duration_sec=req.target_duration_sec,
        style_pack_id=req.style_pack_id,
        routing_profile=req.routing_profile,
    )
    db.add(proj)
    await db.commit()
    await db.refresh(proj)
    # Create project media directory
    (settings.projects_dir / proj.id).mkdir(parents=True, exist_ok=True)
    return {
        "id": proj.id,
        "name": proj.name,
        "created_at": proj.created_at.isoformat(),
        "aspect_ratio": proj.aspect_ratio,
        "resolution": proj.resolution,
        "target_duration_sec": proj.target_duration_sec,
        "style_pack_id": proj.style_pack_id,
        "routing_profile": proj.routing_profile,
        "preview_mode": proj.preview_mode,
        "budget_usd": proj.budget_usd,
    }


@app.get("/projects")
async def list_projects(db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    result = await db.execute(select(Project).options(selectinload(Project.shots)).order_by(Project.created_at.desc()))
    projects = result.scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "created_at": p.created_at.isoformat(),
            "aspect_ratio": p.aspect_ratio,
            "target_duration_sec": p.target_duration_sec,
            "shot_count": len(p.shots),
            "status": "done" if all(s.status == "done" for s in p.shots) else "draft",
        }
        for p in projects
    ]


@app.get("/projects/{project_id}")
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.sources), selectinload(Project.shots))
    )
    proj = result.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "id": proj.id,
        "name": proj.name,
        "created_at": proj.created_at.isoformat(),
        "aspect_ratio": proj.aspect_ratio,
        "resolution": proj.resolution,
        "target_duration_sec": proj.target_duration_sec,
        "style_pack_id": proj.style_pack_id,
        "routing_profile": proj.routing_profile,
        "preview_mode": proj.preview_mode,
        "budget_usd": proj.budget_usd,
        "tokens_used_input": proj.tokens_used_input,
        "tokens_used_output": proj.tokens_used_output,
        "tokens_used_cached": proj.tokens_used_cached,
        "sources": [{"id": s.id, "kind": s.kind, "word_count": s.word_count} for s in proj.sources],
        "shots": [
            {
                "id": s.id,
                "order_index": s.order_index,
                "duration_sec": s.duration_sec,
                "tier": s.tier,
                "status": s.status,
                "prompt_text": s.prompt_text,
                "bridge_strategy": s.bridge_strategy,
                "clip_path": s.clip_path,
                "cost_usd": s.cost_usd,
            }
            for s in sorted(proj.shots, key=lambda x: x.order_index)
        ],
    }


@app.delete("/projects/{project_id}")
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    result = await db.execute(select(Project).where(Project.id == project_id))
    proj = result.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(proj)
    await db.commit()
    # Remove media directory
    proj_dir = settings.projects_dir / project_id
    if proj_dir.exists():
        shutil.rmtree(proj_dir)
    return {"status": "deleted"}


@app.patch("/projects/{project_id}")
async def update_project(
    project_id: str,
    body: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(select(Project).where(Project.id == project_id))
    proj = result.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    for key in (
        "name",
        "aspect_ratio",
        "resolution",
        "target_duration_sec",
        "style_pack_id",
        "routing_profile",
        "preview_mode",
        "budget_usd",
        "trailer_task_id",
        "trailer_url",
    ):
        if key in body:
            setattr(proj, key, body[key])
    proj.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(proj)
    return {"status": "updated"}


# ═══════════════════════════════════════════════════════════════
# Trailer generation (MoneyPrinterTurbo bridge)
# ═══════════════════════════════════════════════════════════════


@app.post("/api/projects/{project_id}/generate-trailer")
async def generate_trailer(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Kick off a trailer generation via MoneyPrinterTurbo."""
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.sources), selectinload(Project.treatments))
    )
    proj = result.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    # Extract logline + synopsis from latest treatment
    treatment = None
    if proj.treatments:
        treatment = max(proj.treatments, key=lambda t: t.created_at)

    logline = ""
    synopsis = ""
    if treatment and treatment.json:
        logline = treatment.json.get("logline", "")
        synopsis = treatment.json.get("synopsis", "") or treatment.json.get("theme", "")

    if not logline:
        # Fallback: use first 200 chars of source text
        source_text = "\n\n".join(s.extracted_text or "" for s in proj.sources)
        logline = (source_text or proj.name)[:200]

    bridge = get_bridge()
    try:
        resp = bridge.generate_video(
            video_subject=logline,
            video_script=synopsis,
            video_concat_mode="sequential",
            video_language="en",
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"MPT bridge failed: {exc}")

    task_id = resp.get("task_id")
    proj.trailer_task_id = task_id
    await db.commit()
    return {"task_id": task_id, "status": "queued"}


@app.get("/api/projects/{project_id}/trailer-status")
async def trailer_status(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Poll MPT for trailer task status."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    proj = result.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    if not proj.trailer_task_id:
        return {"status": "not_started", "task_id": None}

    bridge = get_bridge()
    try:
        mpt_resp = bridge.get_task(proj.trailer_task_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"MPT bridge failed: {exc}")

    data = mpt_resp.get("data", mpt_resp)
    state = data.get("state", "unknown")
    progress = data.get("progress", 0)
    url = data.get("video_url") or data.get("url")
    if url and not proj.trailer_url:
        proj.trailer_url = url
        await db.commit()

    return {
        "task_id": proj.trailer_task_id,
        "status": state,
        "progress": progress,
        "url": url or proj.trailer_url,
    }


@app.get("/api/projects/{project_id}/trailer-download")
async def trailer_download(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return the download URL for the generated trailer."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    proj = result.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    if not proj.trailer_url:
        # Try refreshing from MPT
        if proj.trailer_task_id:
            bridge = get_bridge()
            try:
                mpt_resp = bridge.get_task(proj.trailer_task_id)
                data = mpt_resp.get("data", mpt_resp)
                url = data.get("video_url") or data.get("url")
                if url:
                    proj.trailer_url = url
                    await db.commit()
            except Exception:
                pass

    if not proj.trailer_url:
        raise HTTPException(status_code=404, detail="Trailer not ready or not generated")

    return {"url": proj.trailer_url, "task_id": proj.trailer_task_id}


# ═══════════════════════════════════════════════════════════════
# Sources / Ingest
# ═══════════════════════════════════════════════════════════════


@app.post("/projects/{project_id}/sources")
async def upload_source(
    project_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(select(Project).where(Project.id == project_id))
    proj = result.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    proj_dir = settings.projects_dir / project_id
    raw_path = proj_dir / f"source_{uuid.uuid4().hex}_{file.filename}"
    with open(raw_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    kind = (
        "pdf"
        if file.filename and file.filename.endswith(".pdf")
        else "md"
        if file.filename and file.filename.endswith(".md")
        else "txt"
        if file.filename and file.filename.endswith(".txt")
        else "url"
    )

    normalized_path = proj_dir / f"{raw_path.stem}.md"
    try:
        extracted = await ingest_document(raw_path, normalized_path, kind)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Ingest failed: {exc}")

    src = SourceDoc(
        project_id=project_id,
        kind=kind,
        raw_path=str(raw_path),
        normalized_path=str(normalized_path),
        extracted_text=extracted[:10000] if extracted else None,
        word_count=len(extracted.split()) if extracted else 0,
    )
    db.add(src)
    await db.commit()
    await db.refresh(src)
    return {"id": src.id, "kind": src.kind, "word_count": src.word_count}


# ═══════════════════════════════════════════════════════════════
# Director — Treatment & Storyboard
# ═══════════════════════════════════════════════════════════════


class GenerateTreatmentRequest(BaseModel):
    llm_provider: str | None = None
    style_pack_id: str | None = None
    topic: str = "documentary"


@app.post("/projects/{project_id}/treatment")
async def create_treatment(
    project_id: str,
    req: GenerateTreatmentRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(select(Project).where(Project.id == project_id).options(selectinload(Project.sources)))
    proj = result.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    source_text = "\n\n".join(s.extracted_text or "" for s in proj.sources)
    if not source_text.strip():
        raise HTTPException(status_code=400, detail="No source text available")

    llm_name = req.llm_provider or app_ctx.router.resolve_llm("treatment", proj.routing_profile)
    llm = app_ctx.registry.llm_adapter(llm_name)

    topic = req.topic if hasattr(req, "topic") else "documentary"
    try:
        treatment_json, usage = await generate_treatment(
            llm=llm,
            source_text=source_text,
            style_pack=app_ctx.prefabs.get_style_pack(req.style_pack_id or proj.style_pack_id),
            target_duration=proj.target_duration_sec,
            topic=topic,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Treatment generation failed: {exc}")

    treatment = Treatment(
        project_id=project_id,
        json=treatment_json,
        llm_model=llm_name,
        token_usage=usage.model_dump(),
    )
    db.add(treatment)
    proj.tokens_used_input += usage.input_tokens
    proj.tokens_used_output += usage.output_tokens
    proj.tokens_used_cached += usage.cached_input_tokens
    await db.commit()
    await db.refresh(treatment)
    return {"id": treatment.id, "treatment": treatment_json, "token_usage": usage.model_dump()}


class GenerateStoryboardRequest(BaseModel):
    llm_provider: str | None = None
    treatment_id: str | None = None
    topic: str = "documentary"


@app.post("/projects/{project_id}/storyboard")
async def create_storyboard(
    project_id: str,
    req: GenerateStoryboardRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(select(Project).where(Project.id == project_id))
    proj = result.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    treatment = None
    if req.treatment_id:
        t_result = await db.execute(select(Treatment).where(Treatment.id == req.treatment_id))
        treatment = t_result.scalar_one_or_none()
    if not treatment:
        t_result = await db.execute(
            select(Treatment).where(Treatment.project_id == project_id).order_by(Treatment.created_at.desc())
        )
        treatment = t_result.scalar_one_or_none()
    if not treatment:
        raise HTTPException(status_code=400, detail="No treatment found. Generate one first.")

    # Resolve video capabilities for the active provider
    video_provider = app_ctx.router.resolve_video("hero", proj.routing_profile, proj.preview_mode)
    video_adapter = app_ctx.registry.video_adapter(video_provider)
    capabilities = video_adapter.capabilities

    llm_name = req.llm_provider or app_ctx.router.resolve_llm("storyboard", proj.routing_profile)
    llm = app_ctx.registry.llm_adapter(llm_name)

    topic = req.topic if hasattr(req, "topic") else "documentary"
    try:
        shots_data, usage = await generate_storyboard(
            llm=llm,
            treatment=treatment.json,
            capabilities=capabilities,
            style_pack=app_ctx.prefabs.get_style_pack(proj.style_pack_id),
            topic=topic,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Storyboard generation failed: {exc}")

    # Persist shots
    for idx, s in enumerate(shots_data):
        shot = Shot(
            project_id=project_id,
            order_index=idx,
            duration_sec=s["duration_sec"],
            tier=s.get("tier", "standard"),
            continuity=s.get("continuity", {}),
            prompt_text=s.get("prompt_text", ""),
            prompt_hash=s.get("prompt_hash", ""),
            bridge_strategy=s.get("bridge_strategy", "hard_cut"),
            preferred_bridge=s.get("preferred_bridge", "hard_cut"),
            ref_image_paths=s.get("ref_image_paths", []),
            status="draft",
        )
        db.add(shot)

    proj.tokens_used_input += usage.input_tokens
    proj.tokens_used_output += usage.output_tokens
    proj.tokens_used_cached += usage.cached_input_tokens
    await db.commit()

    return {
        "shot_count": len(shots_data),
        "token_usage": usage.model_dump(),
        "shots": shots_data,
    }


# ═══════════════════════════════════════════════════════════════
# Shots
# ═══════════════════════════════════════════════════════════════


@app.patch("/projects/{project_id}/shots/{shot_id}")
async def update_shot(
    project_id: str,
    shot_id: str,
    body: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update shot fields."""
    result = await db.execute(
        select(Shot).where(Shot.id == shot_id, Shot.project_id == project_id)
    )
    shot = result.scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")
    for key in (
        "order_index",
        "duration_sec",
        "tier",
        "prompt_text",
        "bridge_strategy",
        "preferred_bridge",
        "narration",
        "transition_in",
        "status",
        "error",
    ):
        if key in body:
            setattr(shot, key, body[key])
    await db.commit()
    await db.refresh(shot)
    return {
        "id": shot.id,
        "order_index": shot.order_index,
        "duration_sec": shot.duration_sec,
        "tier": shot.tier,
        "prompt_text": shot.prompt_text,
        "bridge_strategy": shot.bridge_strategy,
        "status": shot.status,
    }


# ═══════════════════════════════════════════════════════════════
# PromptForge
# ═══════════════════════════════════════════════════════════════


class ForgePromptRequest(BaseModel):
    shot_id: str
    continuity_yaml: str | None = None


@app.post("/projects/{project_id}/prompts/forge")
async def forge_prompt(
    project_id: str,
    req: ForgePromptRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(select(Shot).where(Shot.id == req.shot_id, Shot.project_id == project_id))
    shot = result.scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")

    p_result = await db.execute(select(Project).where(Project.id == project_id))
    proj = p_result.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    continuity = ContinuityBible.from_project(project_id, settings.projects_dir)
    if req.continuity_yaml:
        continuity.load_yaml(req.continuity_yaml)

    style_pack = app_ctx.prefabs.get_style_pack(proj.style_pack_id) if proj else None
    pf = PromptForge(continuity=continuity, style_pack=style_pack)

    video_provider = app_ctx.router.resolve_video(shot.tier, proj.routing_profile, proj.preview_mode)
    video_adapter = app_ctx.registry.video_adapter(video_provider)

    try:
        prompt = pf.forge(shot, video_adapter.capabilities)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Prompt forging failed: {exc}")

    shot.prompt_text = prompt
    shot.prompt_hash = pf.hash_prompt(prompt)
    await db.commit()
    return {"shot_id": shot.id, "prompt": prompt, "prompt_hash": shot.prompt_hash}


# ═══════════════════════════════════════════════════════════════
# Render
# ═══════════════════════════════════════════════════════════════


class RenderShotRequest(BaseModel):
    shot_ids: list[str] | None = None  # None = render all draft shots


@app.post("/projects/{project_id}/render")
async def render_project(
    project_id: str,
    req: RenderShotRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(select(Project).where(Project.id == project_id).options(selectinload(Project.shots)))
    proj = result.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    shots = proj.shots
    if req.shot_ids:
        shots = [s for s in shots if s.id in req.shot_ids]
    else:
        shots = [s for s in shots if s.status in ("draft", "failed")]

    if not shots:
        return {"status": "nothing_to_render", "message": "All shots are already rendered"}

    # Pre-flight checks
    try:
        run_preflight(proj)
    except PreflightError as exc:
        raise HTTPException(status_code=507, detail=str(exc))

    # Create render job
    job = RenderJob(project_id=project_id, status="running")
    db.add(job)
    await db.commit()
    await db.refresh(job)

    pipeline = RenderPipeline(
        registry=app_ctx.registry,
        router=app_ctx.router,
        project_dir=settings.projects_dir / project_id,
    )

    # Launch async render
    background_tasks.add_task(_run_render, pipeline, project_id, [s.id for s in shots], job.id)
    return {"job_id": job.id, "status": "queued", "shot_count": len(shots)}


async def _run_render(
    pipeline: RenderPipeline,
    project_id: str,
    shot_ids: list[str],
    job_id: str,
) -> None:
    """Background render task."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Project).where(Project.id == project_id).options(selectinload(Project.shots))
        )
        proj = result.scalar_one()
        shots = [s for s in proj.shots if s.id in shot_ids]
        j_result = await session.execute(select(RenderJob).where(RenderJob.id == job_id))
        job = j_result.scalar_one()

        try:
            total_cost = 0.0
            for shot in shots:
                shot.status = "rendering"
                shot.render_started_at = datetime.now(timezone.utc).replace(tzinfo=None)
                await session.commit()
                try:
                    result = await pipeline.render_shot(
                        shot=shot,
                        project=proj,
                    )
                    shot.clip_path = str(result.clip_path)
                    shot.last_frame_path = str(result.last_frame_path) if result.last_frame_path else None
                    shot.status = "done"
                    shot.cost_usd = result.cost_usd
                    shot.provider_id = result.provider_id
                    total_cost += result.cost_usd
                except Exception as exc:
                    shot.status = "failed"
                    shot.error = str(exc)
                shot.render_finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
                await session.commit()

            job.status = "done"
            job.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
            job.total_cost_usd = total_cost
            await session.commit()
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            job.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await session.commit()


# ═══════════════════════════════════════════════════════════════
# Stitch
# ═══════════════════════════════════════════════════════════════


class StitchRequest(BaseModel):
    output_name: str = "master"


@app.post("/projects/{project_id}/stitch")
async def stitch_project(
    project_id: str,
    req: StitchRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(select(Project).where(Project.id == project_id).options(selectinload(Project.shots)))
    proj = result.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    shots = sorted([s for s in proj.shots if s.clip_path], key=lambda x: x.order_index)
    if not shots:
        raise HTTPException(status_code=400, detail="No rendered clips to stitch")

    style_pack = app_ctx.prefabs.get_style_pack(proj.style_pack_id)
    stitcher = Stitcher(
        project_dir=settings.projects_dir / project_id,
        transitions_dir=settings.prefabs_dir / "transitions",
        prefabs_dir=settings.prefabs_dir,
    )
    output_path = settings.projects_dir / project_id / f"{req.output_name}.mp4"
    timeline = stitcher.assemble(shots, output_path, proj.aspect_ratio, style_pack=style_pack)

    # Save sidecar
    sidecar_path = settings.projects_dir / project_id / f"{req.output_name}.timeline.json"
    with open(sidecar_path, "w") as f:
        json.dump(timeline, f, indent=2)

    return {
        "output_path": str(output_path),
        "sidecar_path": str(sidecar_path),
        "duration_sec": timeline.get("duration_sec", 0),
        "shot_count": len(shots),
    }


# ═══════════════════════════════════════════════════════════════
# Narration
# ═══════════════════════════════════════════════════════════════


class NarrationRequest(BaseModel):
    shot_ids: list[str] | None = None


@app.post("/projects/{project_id}/narration")
async def generate_narration(
    project_id: str,
    req: NarrationRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(select(Project).where(Project.id == project_id).options(selectinload(Project.shots)))
    proj = result.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    shots = proj.shots
    if req.shot_ids:
        shots = [s for s in shots if s.id in req.shot_ids]

    pipeline = RenderPipeline(
        registry=app_ctx.registry,
        router=app_ctx.router,
        project_dir=settings.projects_dir / project_id,
    )

    generated: list[dict[str, Any]] = []
    for shot in shots:
        shot_dir = settings.projects_dir / project_id / "shots" / shot.id
        path = await pipeline._generate_narration(shot, shot_dir)
        if path:
            generated.append({"shot_id": shot.id, "path": str(path)})

    return {"generated": generated}


# ═══════════════════════════════════════════════════════════════
# Reference Images
# ═══════════════════════════════════════════════════════════════


class RefImagesRequest(BaseModel):
    shot_ids: list[str] | None = None


@app.post("/projects/{project_id}/ref-images")
async def generate_ref_images(
    project_id: str,
    req: RefImagesRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(select(Project).where(Project.id == project_id).options(selectinload(Project.shots)))
    proj = result.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    shots = proj.shots
    if req.shot_ids:
        shots = [s for s in shots if s.id in req.shot_ids]

    style_pack = app_ctx.prefabs.get_style_pack(proj.style_pack_id)
    pipeline = RenderPipeline(
        registry=app_ctx.registry,
        router=app_ctx.router,
        project_dir=settings.projects_dir / project_id,
    )

    generated: list[dict[str, Any]] = []
    for shot in shots:
        shot_dir = settings.projects_dir / project_id / "shots" / shot.id
        path = await pipeline._generate_reference_images(shot, shot_dir, style_pack)
        if path:
            if not shot.ref_image_paths:
                shot.ref_image_paths = []
            if str(path) not in shot.ref_image_paths:
                shot.ref_image_paths.append(str(path))
            await db.commit()
            generated.append({"shot_id": shot.id, "path": str(path)})

    return {"generated": generated}


# ═══════════════════════════════════════════════════════════════
# Extend
# ═══════════════════════════════════════════════════════════════


class ExtendShotRequest(BaseModel):
    shot_id: str
    extra_seconds: int = 7


@app.post("/projects/{project_id}/extend")
async def extend_shot(
    project_id: str,
    req: ExtendShotRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(select(Shot).where(Shot.id == req.shot_id, Shot.project_id == project_id))
    shot = result.scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="Shot not found")
    if not shot.clip_path:
        raise HTTPException(status_code=400, detail="Shot has not been rendered yet")

    p_result = await db.execute(select(Project).where(Project.id == project_id))
    proj = p_result.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    provider_id = shot.provider_id or app_ctx.router.resolve_video(shot.tier, proj.routing_profile, proj.preview_mode)
    adapter = app_ctx.registry.video_adapter(provider_id)
    ext = ExtendPipeline(adapter)

    try:
        ext_result = await ext.run(
            Path(shot.clip_path),
            shot.prompt_text or "",
            req.extra_seconds,
        )
    except CapabilityError:
        raise HTTPException(
            status_code=400,
            detail=f"Adapter {provider_id} does not support extend",
        )

    original = Path(shot.clip_path)
    extended_path = original.with_name(f"{original.stem}_extended.mp4")
    shutil.copy2(ext_result.clip_path, extended_path)

    return {
        "extended_clip_path": str(extended_path),
        "duration_sec": ext_result.duration_sec,
        "provider_id": provider_id,
    }


# ═══════════════════════════════════════════════════════════════
# B-Roll (MoneyPrinterTurbo Bridge)
# ═══════════════════════════════════════════════════════════════


@app.post("/api/scenes/{scene_id}/generate-broll")
async def generate_broll_for_scene(
    scene_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate a B-roll clip for a single scene (shot)."""
    result = await db.execute(select(Shot).where(Shot.id == scene_id))
    shot = result.scalar_one_or_none()
    if not shot:
        raise HTTPException(status_code=404, detail="Scene not found")

    p_result = await db.execute(select(Project).where(Project.id == shot.project_id))
    proj = p_result.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    clip = BrollClip(
        shot_id=scene_id,
        project_id=proj.id,
        status="rendering",
    )
    db.add(clip)
    await db.commit()
    await db.refresh(clip)

    # Launch async generation
    background_tasks.add_task(_run_broll_generation, clip.id, scene_id, proj.id)
    return {"clip_id": clip.id, "status": "queued"}


async def _run_broll_generation(clip_id: str, shot_id: str, project_id: str) -> None:
    """Background B-roll generation task."""
    async with AsyncSessionLocal() as session:
        c_result = await session.execute(select(BrollClip).where(BrollClip.id == clip_id))
        clip = c_result.scalar_one()
        s_result = await session.execute(select(Shot).where(Shot.id == shot_id))
        shot = s_result.scalar_one()
        p_result = await session.execute(select(Project).where(Project.id == project_id))
        proj = p_result.scalar_one()

        bridge = MPTBrollBridge(
            project_dir=settings.projects_dir / project_id,
        )
        try:
            result = await bridge.generate_for_shot(shot, proj)
            clip.clip_path = result["clip_path"]
            clip.thumbnail_path = result["thumbnail_path"]
            clip.prompt_text = result["prompt_text"]
            clip.cost_usd = result["cost_usd"]
            clip.provider_id = result["provider_id"]
            clip.duration_sec = result["duration_sec"]
            clip.clip_meta = result["metadata"]
            clip.status = "done"
        except Exception as exc:
            clip.status = "failed"
            clip.error = str(exc)
        await session.commit()


@app.post("/api/projects/{project_id}/generate-all-broll")
async def generate_all_broll(
    project_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate B-roll clips for every shot in a project."""
    result = await db.execute(
        select(Project).where(Project.id == project_id).options(selectinload(Project.shots))
    )
    proj = result.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    queued: list[str] = []
    for shot in proj.shots:
        clip = BrollClip(
            shot_id=shot.id,
            project_id=proj.id,
            status="rendering",
        )
        db.add(clip)
        await db.commit()
        await db.refresh(clip)
        background_tasks.add_task(_run_broll_generation, clip.id, shot.id, proj.id)
        queued.append(clip.id)

    return {"queued": queued, "count": len(queued)}


@app.get("/api/scenes/{scene_id}/broll")
async def list_scene_broll(scene_id: str, db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    """List all B-roll clips generated for a scene (shot)."""
    result = await db.execute(select(BrollClip).where(BrollClip.shot_id == scene_id).order_by(BrollClip.created_at.desc()))
    clips = result.scalars().all()
    return [
        {
            "id": c.id,
            "shot_id": c.shot_id,
            "project_id": c.project_id,
            "status": c.status,
            "clip_path": c.clip_path,
            "thumbnail_path": c.thumbnail_path,
            "prompt_text": c.prompt_text,
            "cost_usd": c.cost_usd,
            "provider_id": c.provider_id,
            "duration_sec": c.duration_sec,
            "metadata": c.clip_meta,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in clips
    ]


@app.get("/api/broll/{clip_id}/download")
async def download_broll(clip_id: str, db: AsyncSession = Depends(get_db)) -> FileResponse:
    """Download a generated B-roll clip."""
    result = await db.execute(select(BrollClip).where(BrollClip.id == clip_id))
    clip = result.scalar_one_or_none()
    if not clip or not clip.clip_path:
        raise HTTPException(status_code=404, detail="Clip not found")
    path = Path(clip.clip_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Clip file not found")
    return FileResponse(path, media_type="video/mp4", filename=path.name)


# ═══════════════════════════════════════════════════════════════
# Routing
# ═══════════════════════════════════════════════════════════════


@app.get("/routing")
async def get_routing() -> dict[str, Any]:
    cfg = app_ctx.router.config.copy()
    # Inject descriptions from profile metadata
    for name, profile in app_ctx.router.profiles.items():
        if name in cfg.get("profiles", {}):
            cfg["profiles"][name]["_description"] = profile.get("description", "")
            cfg["profiles"][name]["_video_providers"] = {
                k: v for k, v in profile.get("video", {}).items() if not k.startswith("post_")
            }
            cfg["profiles"][name]["_post_process"] = {
                k: v for k, v in profile.get("video", {}).items() if k.startswith("post_")
            }
    return cfg


@app.put("/routing")
async def update_routing(body: dict[str, Any]) -> dict[str, Any]:
    app_ctx.router.update(body)
    app_ctx.router.save(settings.data_dir / "routing.yaml")
    return {"status": "updated"}


@app.get("/routing/profiles")
async def list_profiles() -> list[str]:
    return list(app_ctx.router.profiles.keys())


# ═══════════════════════════════════════════════════════════════
# Prefabs
# ═══════════════════════════════════════════════════════════════


@app.get("/prefabs/style-packs")
async def list_style_packs() -> list[dict[str, Any]]:
    return app_ctx.prefabs.list_style_packs()


@app.get("/prefabs/grammars")
async def list_grammars() -> list[dict[str, Any]]:
    return app_ctx.prefabs.list_grammars()


@app.get("/prefabs/transitions")
async def list_transitions() -> list[dict[str, Any]]:
    return app_ctx.prefabs.list_transitions()


BUNDLED_PREFABS_DIR = Path(__file__).parent.parent / "prefabs"


@app.get("/api/prefabs")
async def get_prefabs_manifest() -> dict[str, Any]:
    """Return the bundled prefabs manifest."""
    manifest_path = BUNDLED_PREFABS_DIR / "MANIFEST.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Manifest not found")
    data: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    return data


@app.get("/api/prefabs/{category}/{prefab_id}")
async def get_prefab(category: str, prefab_id: str) -> Response:
    """Return a specific prefab file by category and id."""
    manifest_path = BUNDLED_PREFABS_DIR / "MANIFEST.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Manifest not found")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    prefab = next(
        (
            p
            for p in manifest.get("prefabs", [])
            if p["category"] == category and p["id"] == prefab_id
        ),
        None,
    )
    if not prefab:
        raise HTTPException(status_code=404, detail="Prefab not found")
    file_path = BUNDLED_PREFABS_DIR / prefab["path"]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Prefab file not found")
    content = file_path.read_text(encoding="utf-8")
    suffix = file_path.suffix
    if suffix == ".json":
        media_type = "application/json"
    elif suffix in (".yaml", ".yml"):
        media_type = "text/yaml"
    elif suffix == ".py":
        media_type = "text/x-python"
    else:
        media_type = "text/plain"
    return Response(content=content, media_type=media_type)


# ═══════════════════════════════════════════════════════════════
# StackBuilder — intelligent profile recommendation
# ═══════════════════════════════════════════════════════════════


@app.post("/stackbuilder/recommend")
async def stackbuilder_recommend(body: dict[str, Any]) -> dict[str, Any]:
    """Get ranked profile recommendations for project constraints."""
    constraints = ProjectConstraints(
        topic=body.get("topic", "documentary"),
        target_duration_min=body.get("target_duration_min", 1.0),
        budget_usd=body.get("budget_usd", 5.00),
        deadline_hours=body.get("deadline_hours", 24.0),
        vram_available_gb=body.get("vram_available_gb", 0),
        prioritize=body.get("prioritize", "balanced"),
        source_count=body.get("source_count", 1),
        word_count=body.get("word_count", 0),
    )
    builder = StackBuilder()
    scores = builder.recommend(constraints)
    return {
        "constraints": {
            "topic": constraints.topic,
            "target_duration_min": constraints.target_duration_min,
            "budget_usd": constraints.budget_usd,
            "deadline_hours": constraints.deadline_hours,
            "vram_available_gb": constraints.vram_available_gb,
            "prioritize": constraints.prioritize,
        },
        "recommendations": [
            {
                "name": s.name,
                "overall_score": s.overall_score,
                "dimension_scores": s.dimension_scores,
                "recommendation": s.recommendation,
                "warnings": s.warnings,
                "description": s.tradeoffs.description,
                "primary_use_case": s.tradeoffs.primary_use_case,
            }
            for s in scores[:5]  # top 5
        ],
        "defaults": builder.get_defaults(constraints.topic),
    }


@app.get("/stackbuilder/topics")
async def stackbuilder_topics() -> dict[str, Any]:
    """List available topics and their default configurations."""
    builder = StackBuilder()
    topics = ["documentary", "explainer", "archival", "news", "cinematic", "research", "tutorial", "historical"]
    return {"topics": {t: builder.get_defaults(t) for t in topics}}


@app.get("/stackbuilder/profiles/{profile_name}")
async def stackbuilder_profile_detail(profile_name: str) -> dict[str, Any]:
    """Get detailed tradeoff data for a specific profile."""
    from backend.stackbuilder.profiles import PROFILE_TRADEOFFS

    if profile_name not in PROFILE_TRADEOFFS:
        raise HTTPException(status_code=404, detail="Profile not found")
    t = PROFILE_TRADEOFFS[profile_name]
    return {
        "name": profile_name,
        "quality_score": t.quality_score,
        "speed_score": t.speed_score,
        "cost_score": t.cost_score,
        "depth_score": t.depth_score,
        "local_dependency": t.local_dependency,
        "vram_required_gb": t.vram_required_gb,
        "max_recommended_duration_min": t.max_recommended_duration_min,
        "primary_use_case": t.primary_use_case,
        "description": t.description,
    }


# ═══════════════════════════════════════════════════════════════
# Telemetry
# ═══════════════════════════════════════════════════════════════


@app.get("/telemetry")
async def get_telemetry() -> dict[str, Any]:
    """Return current session telemetry stats."""
    return session_summary()


# ═══════════════════════════════════════════════════════════════
# Project Bundles
# ═══════════════════════════════════════════════════════════════


@app.post("/projects/{project_id}/export-bundle")
async def export_bundle(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Export a project as a .cineforge bundle."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    proj = result.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    bundle_path = await export_project_bundle(project_id, db)
    return FileResponse(
        bundle_path,
        media_type="application/zip",
        filename=f"{proj.name or project_id}.cineforge",
    )


@app.post("/projects/import-bundle")
async def import_bundle(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Import a project from a .cineforge bundle."""
    if not file.filename or not file.filename.endswith(".cineforge"):
        raise HTTPException(status_code=400, detail="File must have .cineforge extension")
    tmp_path = settings.projects_dir / f"import_{uuid.uuid4().hex}.cineforge"
    with open(tmp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        proj = await import_project_bundle(tmp_path, db)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Import failed: {exc}")
    finally:
        tmp_path.unlink(missing_ok=True)
    return {
        "id": proj.id,
        "name": proj.name,
        "status": "imported",
    }


# ═══════════════════════════════════════════════════════════════
# Diagnostics & Onboarding
# ═══════════════════════════════════════════════════════════════


@app.get("/diagnostics")
async def run_diagnostics() -> dict[str, Any]:
    """Run full system diagnostics and return actionable report."""
    from backend.settings import get_settings

    settings = get_settings()
    engine = DiagnosticsEngine(settings.data_dir, settings.projects_dir)
    results = await engine.run_all()
    ok_count = sum(1 for r in results if r.status == "ok")
    warning_count = sum(1 for r in results if r.status == "warning")
    error_count = sum(1 for r in results if r.status == "error")
    return {
        "overall_status": "ready" if error_count == 0 else "needs_attention" if error_count < 3 else "blocked",
        "summary": {
            "ok": ok_count,
            "warning": warning_count,
            "error": error_count,
            "total": len(results),
        },
        "checks": [r.to_dict() for r in results],
        "next_steps": [r.fix for r in results if r.status in ("warning", "error") and r.fix],
    }


@app.get("/diagnostics/quick")
async def quick_diagnostics() -> dict[str, Any]:
    """Quick health check for onboarding wizard."""
    try:
        import urllib.request

        with urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=2) as resp:
            backend_ok = b"ok" in resp.read()
    except Exception:
        backend_ok = False
    return {
        "backend_running": backend_ok,
        "port": 8765,
        "timestamp": __import__("datetime").datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
# Media serving
# ═══════════════════════════════════════════════════════════════


@app.get("/media/{project_id}/{filename}")
async def serve_media(project_id: str, filename: str) -> FileResponse:
    path = settings.projects_dir / project_id / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=False,
    )
