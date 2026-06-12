"""FastAPI entry point for CineForge backend."""

from __future__ import annotations

import asyncio
import contextvars
import html
import json
import logging
import os
import shutil
import uuid
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Awaitable, Callable

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile, BackgroundTasks
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.settings import get_settings
from backend.models.project import init_db, Project, Shot, SourceDoc, Treatment, RenderJob, BrollClip, ExportJob
from backend.adapters.registry import get_registry
from backend.adapters.protocols import CapabilityError
from backend.ingest.pipeline import ingest_document
from backend.ingest.lookbook import build_treatment_from_lookbook, convert_lookbook_to_shots, parse_lookbook_shot_graph
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
from backend.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
    conflict_error_handler,
    http_exception_handler,
    not_found_handler,
    request_validation_error_handler,
    unhandled_exception_handler,
    validation_error_handler,
)
from backend.middleware import RateLimitMiddleware, SecurityHeadersMiddleware
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

# ── Exception handlers ──────────────────────────────────────────
app.add_exception_handler(NotFoundError, not_found_handler)
app.add_exception_handler(ValidationError, validation_error_handler)
app.add_exception_handler(ConflictError, conflict_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, request_validation_error_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# ── CORS ────────────────────────────────────────────────────────
# In production, do not allow wildcard origins.
_cors_origins = ["*"]
if os.getenv("CINEFORGE_ENV", "development").lower() == "production":
    _cors_origins = os.getenv("CINEFORGE_CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)

# ── Security & rate limiting ────────────────────────────────────
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

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
    name: str = Field(..., max_length=200)
    aspect_ratio: str = Field(default="16:9", max_length=20)
    resolution: str = Field(default="1080p", max_length=20)
    target_duration_sec: int = Field(default=60, ge=1, le=36000)
    style_pack_id: str | None = Field(default=None, max_length=200)
    routing_profile: str = Field(default=settings.default_routing_profile, max_length=100)


@app.post("/projects")
async def create_project(
    req: CreateProjectRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    proj = Project(
        name=html.escape(req.name),
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
            value = body[key]
            if key == "name" and isinstance(value, str):
                if len(value) > 200:
                    raise HTTPException(status_code=400, detail="Project name must be under 200 characters")
                value = html.escape(value)
            if key == "target_duration_sec" and isinstance(value, int):
                if value < 1 or value > 36000:
                    raise HTTPException(status_code=400, detail="target_duration_sec must be between 1 and 36000")
            setattr(proj, key, value)
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
    llm_provider: str | None = Field(default=None, max_length=100)
    style_pack_id: str | None = Field(default=None, max_length=200)
    topic: str = Field(default="documentary", max_length=200)


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
    llm_provider: str | None = Field(default=None, max_length=100)
    treatment_id: str | None = Field(default=None, max_length=100)
    topic: str = Field(default="documentary", max_length=200)


class IngestLookbookRequest(BaseModel):
    shot_graph: dict[str, Any]
    replace_existing_shots: bool = Field(default=True)


@app.post("/projects/{project_id}/ingest/lookbook")
async def ingest_lookbook_shots(
    project_id: str,
    req: IngestLookbookRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Import lookBOOK shot_graph.json as CineForge storyboard shots."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    proj = result.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        parse_lookbook_shot_graph(req.shot_graph)
        shots_data = convert_lookbook_to_shots(req.shot_graph)
        treatment_json = build_treatment_from_lookbook(req.shot_graph)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if req.replace_existing_shots:
        existing = await db.execute(select(Shot).where(Shot.project_id == project_id))
        for shot in existing.scalars().all():
            await db.delete(shot)

    treatment = Treatment(
        project_id=project_id,
        json=treatment_json,
        llm_model="lookbook.import",
        token_usage={"input_tokens": 0, "output_tokens": 0, "cached_input_tokens": 0},
    )
    db.add(treatment)
    await db.flush()

    for s in shots_data:
        shot = Shot(
            project_id=project_id,
            order_index=s["order_index"],
            duration_sec=s["duration_sec"],
            tier=s.get("tier", "standard"),
            continuity=s.get("continuity", {}),
            prompt_text=s.get("prompt_text", ""),
            prompt_hash=s.get("prompt_hash", ""),
            bridge_strategy=s.get("bridge_strategy", "hard_cut"),
            preferred_bridge=s.get("preferred_bridge", "hard_cut"),
            ref_image_paths=s.get("ref_image_paths", []),
            narration=s.get("narration"),
            transition_in=s.get("transition_in", "hard_cut"),
            status="draft",
        )
        db.add(shot)

    await db.commit()
    return {
        "shot_count": len(shots_data),
        "treatment_id": treatment.id,
        "source": "lookbook",
        "shots": shots_data,
    }


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
            value = body[key]
            if key in ("prompt_text", "narration", "error") and isinstance(value, str):
                if len(value) > 5000:
                    raise HTTPException(status_code=400, detail=f"{key} must be under 5000 characters")
                value = html.escape(value)
            if key == "duration_sec" and isinstance(value, (int, float)):
                if value <= 0 or value > 36000:
                    raise HTTPException(status_code=400, detail="duration_sec must be between 1 and 36000 seconds")
            setattr(shot, key, value)
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
    shot_id: str = Field(..., max_length=100)
    continuity_yaml: str | None = Field(default=None, max_length=5000)


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
    shot_ids: list[str] | None = Field(default=None, max_length=100)  # None = render all draft shots


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
    output_name: str = Field(default="master", max_length=200)


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
    shot_ids: list[str] | None = Field(default=None, max_length=100)


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
    shot_ids: list[str] | None = Field(default=None, max_length=100)


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
    shot_id: str = Field(..., max_length=100)
    extra_seconds: int = Field(default=7, ge=1, le=300)


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
async def list_scene_broll(
    scene_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List B-roll clips generated for a scene (shot)."""
    result = await db.execute(
        select(BrollClip)
        .where(BrollClip.shot_id == scene_id)
        .order_by(BrollClip.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
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
# Export & Distribution
# ═══════════════════════════════════════════════════════════════


class ExportRequest(BaseModel):
    type: str = Field(..., max_length=50)


@app.post("/api/projects/{project_id}/export")
async def queue_export(
    project_id: str,
    req: ExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(select(Project).where(Project.id == project_id))
    proj = result.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    if req.type not in ("mp4", "archive", "stills", "edl"):
        raise HTTPException(status_code=400, detail="Invalid export type")

    job = ExportJob(project_id=project_id, type=req.type, status="queued")
    db.add(job)
    await db.commit()
    await db.refresh(job)

    background_tasks.add_task(_run_export, job.id, project_id, req.type)
    return {"job_id": job.id, "status": "queued", "type": req.type}


@app.get("/api/projects/{project_id}/exports")
async def list_exports(project_id: str, db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    result = await db.execute(select(Project).where(Project.id == project_id))
    proj = result.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(
        select(ExportJob).where(ExportJob.project_id == project_id).order_by(ExportJob.created_at.desc())
    )
    jobs = result.scalars().all()
    return [
        {
            "id": j.id,
            "project_id": j.project_id,
            "type": j.type,
            "status": j.status,
            "progress": j.progress,
            "output_url": j.output_url,
            "output_size": j.output_size,
            "error_message": j.error_message,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
        }
        for j in jobs
    ]


@app.get("/api/exports/{job_id}")
async def get_export_status(job_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    result = await db.execute(select(ExportJob).where(ExportJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")
    return {
        "id": job.id,
        "project_id": job.project_id,
        "type": job.type,
        "status": job.status,
        "progress": job.progress,
        "output_url": job.output_url,
        "output_size": job.output_size,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@app.get("/api/exports/{job_id}/download")
async def download_export(job_id: str, db: AsyncSession = Depends(get_db)) -> FileResponse:
    result = await db.execute(select(ExportJob).where(ExportJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Export not ready")
    if not job.output_url:
        raise HTTPException(status_code=404, detail="Output file not found")
    path = Path(job.output_url)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Output file missing")

    media_type = "application/octet-stream"
    if job.type == "mp4":
        media_type = "video/mp4"
    elif job.type == "edl":
        media_type = "text/plain"
    elif job.type in ("archive", "stills"):
        media_type = "application/zip"

    return FileResponse(path, media_type=media_type, filename=path.name)


@app.delete("/api/exports/{job_id}")
async def delete_export(job_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    result = await db.execute(select(ExportJob).where(ExportJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")

    if job.output_url:
        path = Path(job.output_url)
        if path.exists():
            path.unlink(missing_ok=True)

    await db.delete(job)
    await db.commit()
    return {"status": "deleted"}


async def _run_export(job_id: str, project_id: str, export_type: str) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ExportJob).where(ExportJob.id == job_id))
        job = result.scalar_one()
        settings = get_settings()
        exports_dir = settings.projects_dir / project_id / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)

        try:
            job.status = "processing"
            await session.commit()

            for i in range(1, 21):
                job.progress = i * 5.0
                await session.commit()
                await asyncio.sleep(0.5)

            if export_type == "mp4":
                output_path = exports_dir / f"{project_id}_export.mp4"
                master_path = settings.projects_dir / project_id / "master.mp4"
                if master_path.exists():
                    shutil.copy2(master_path, output_path)
                else:
                    output_path.write_bytes(b"")
                job.output_url = str(output_path)
                job.output_size = output_path.stat().st_size

            elif export_type == "archive":
                output_path = await _create_archive(session, project_id, exports_dir)
                job.output_url = str(output_path)
                job.output_size = output_path.stat().st_size

            elif export_type == "stills":
                output_path = await _create_stills(session, project_id, exports_dir)
                job.output_url = str(output_path)
                job.output_size = output_path.stat().st_size

            elif export_type == "edl":
                output_path = await _create_edl(session, project_id, exports_dir)
                job.output_url = str(output_path)
                job.output_size = output_path.stat().st_size

            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            job.progress = 100.0
            await session.commit()
        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)
            job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await session.commit()


async def _create_archive(session: AsyncSession, project_id: str, exports_dir: Path) -> Path:
    output_path = exports_dir / f"{project_id}_archive.zip"
    result = await session.execute(
        select(Project).where(Project.id == project_id).options(selectinload(Project.shots), selectinload(Project.sources))
    )
    proj = result.scalar_one()
    settings = get_settings()
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        manifest = {
            "project": {
                "id": proj.id,
                "name": proj.name,
                "aspect_ratio": proj.aspect_ratio,
                "resolution": proj.resolution,
                "target_duration_sec": proj.target_duration_sec,
                "created_at": proj.created_at.isoformat() if proj.created_at else None,
            },
            "shots": [
                {
                    "id": s.id,
                    "order_index": s.order_index,
                    "duration_sec": s.duration_sec,
                    "tier": s.tier,
                    "prompt_text": s.prompt_text,
                    "clip_path": s.clip_path,
                    "bridge_strategy": s.bridge_strategy,
                    "transition_in": s.transition_in,
                }
                for s in proj.shots
            ],
            "sources": [
                {
                    "id": s.id,
                    "kind": s.kind,
                    "extracted_text": s.extracted_text,
                    "word_count": s.word_count,
                }
                for s in proj.sources
            ],
        }
        zf.writestr("project.json", json.dumps(manifest, indent=2))
        proj_dir = settings.projects_dir / project_id
        if proj_dir.exists():
            for file_path in proj_dir.rglob("*"):
                if file_path.is_file() and file_path.suffix not in (".edl", ".zip") and "exports" not in str(file_path.relative_to(proj_dir)).split("/"):
                    arcname = "assets/" + str(file_path.relative_to(proj_dir)).replace("\\", "/")
                    zf.write(file_path, arcname)
    return output_path


async def _create_stills(session: AsyncSession, project_id: str, exports_dir: Path) -> Path:
    output_path = exports_dir / f"{project_id}_stills.zip"
    result = await session.execute(select(Project).where(Project.id == project_id).options(selectinload(Project.shots)))
    proj = result.scalar_one()
    png_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for shot in proj.shots:
            png_name = f"shot_{shot.order_index:03d}.png"
            zf.writestr(png_name, png_data)
    return output_path


async def _create_edl(session: AsyncSession, project_id: str, exports_dir: Path) -> Path:
    output_path = exports_dir / f"{project_id}.edl"
    result = await session.execute(select(Project).where(Project.id == project_id).options(selectinload(Project.shots)))
    proj = result.scalar_one()
    edl_content = _generate_edl(proj)
    output_path.write_text(edl_content, encoding="utf-8")
    return output_path


def _generate_edl(project: Project) -> str:
    lines = []
    lines.append(f"TITLE:   {project.name or 'Untitled'}")
    lines.append("FCM: NON-DROP FRAME")
    lines.append("")

    record_time = 0.0

    for idx, shot in enumerate(sorted(project.shots, key=lambda s: s.order_index)):
        event_num = idx + 1
        reel = f"SHOT{shot.order_index + 1:03d}"[:8]
        duration = shot.duration_sec or 5
        source_in = _seconds_to_tc(0.0)
        source_out = _seconds_to_tc(duration)
        record_in = _seconds_to_tc(record_time)
        record_out = _seconds_to_tc(record_time + duration)

        transition = shot.transition_in or shot.bridge_strategy or "hard_cut"
        if transition in ("dissolve", "cross_dissolve", "cross_dissolve_300ms", "dip_to_black"):
            lines.append(
                f"{event_num:03d}  {reel:8s} V     D    030 {source_in} {source_out} {record_in} {record_out}"
            )
        elif transition in ("wipe", "whip_pan"):
            lines.append(
                f"{event_num:03d}  {reel:8s} V     W    030 {source_in} {source_out} {record_in} {record_out}"
            )
        else:
            lines.append(
                f"{event_num:03d}  {reel:8s} V     C        {source_in} {source_out} {record_in} {record_out}"
            )

        clip_name = shot.clip_path or f"shot_{shot.order_index:03d}.mp4"
        lines.append(f"* FROM CLIP NAME: {clip_name}")
        if shot.prompt_text:
            lines.append(f"* DESCRIPTION: {shot.prompt_text[:64]}")
        lines.append("")

        if transition in ("dissolve", "cross_dissolve", "cross_dissolve_300ms", "dip_to_black"):
            record_time += max(duration - 1.0, 0)
        else:
            record_time += duration

    return "\n".join(lines)


def _seconds_to_tc(seconds: float) -> str:
    total_frames = int(seconds * 30)
    hours = total_frames // (30 * 3600)
    minutes = (total_frames % (30 * 3600)) // (30 * 60)
    secs = (total_frames % (30 * 60)) // 30
    frames = total_frames % 30
    return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"


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
