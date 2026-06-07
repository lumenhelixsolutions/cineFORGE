"""SQLAlchemy 2.x mapped models using mapped_column."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import String, Integer, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON


class Base(DeclarativeBase):
    pass


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    style_pack_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    aspect_ratio: Mapped[str] = mapped_column(String(10), default="16:9")
    resolution: Mapped[str] = mapped_column(String(10), default="1080p")
    target_duration_sec: Mapped[int] = mapped_column(Integer, default=60)
    preview_mode: Mapped[bool] = mapped_column(default=False)
    routing_profile: Mapped[str] = mapped_column(String(50), default="hybrid")
    budget_usd: Mapped[float] = mapped_column(default=1.00)
    tokens_used_input: Mapped[int] = mapped_column(Integer, default=0)
    tokens_used_output: Mapped[int] = mapped_column(Integer, default=0)
    tokens_used_cached: Mapped[int] = mapped_column(Integer, default=0)
    trailer_task_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    trailer_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    sources: Mapped[list[SourceDoc]] = relationship("SourceDoc", back_populates="project", cascade="all, delete-orphan")
    treatments: Mapped[list[Treatment]] = relationship(
        "Treatment", back_populates="project", cascade="all, delete-orphan"
    )
    shots: Mapped[list[Shot]] = relationship("Shot", back_populates="project", cascade="all, delete-orphan")
    renders: Mapped[list[RenderJob]] = relationship("RenderJob", back_populates="project", cascade="all, delete-orphan")
    exports: Mapped[list[ExportJob]] = relationship("ExportJob", back_populates="project", cascade="all, delete-orphan")


class SourceDoc(Base):
    __tablename__ = "source_docs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)  # pdf, md, url, txt
    raw_path: Mapped[str] = mapped_column(String(512), nullable=False)
    normalized_path: Mapped[str] = mapped_column(String(512), nullable=False)
    embedding_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(String(10000), nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, default=0)

    project: Mapped[Project] = relationship("Project", back_populates="sources")


class Treatment(Base):
    __tablename__ = "treatments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    json: Mapped[dict[str, Any]] = mapped_column(SQLiteJSON, default=dict)
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False)
    token_usage: Mapped[dict[str, Any]] = mapped_column(SQLiteJSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    project: Mapped[Project] = relationship("Project", back_populates="treatments")


class Shot(Base):
    __tablename__ = "shots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    tier: Mapped[str] = mapped_column(String(20), default="standard")  # hero, standard, broll, title
    continuity: Mapped[dict[str, Any]] = mapped_column(SQLiteJSON, default=dict)
    prompt_text: Mapped[str] = mapped_column(String(2000), default="")
    prompt_hash: Mapped[str] = mapped_column(String(64), default="")
    ref_image_paths: Mapped[list[str]] = mapped_column(SQLiteJSON, default=list)
    bridge_strategy: Mapped[str] = mapped_column(String(30), default="hard_cut")
    preferred_bridge: Mapped[str] = mapped_column(String(30), default="hard_cut")
    narration: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    transition_in: Mapped[str] = mapped_column(String(30), default="hard_cut")
    clip_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_frame_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, queued, rendering, done, failed
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    cost_usd: Mapped[float] = mapped_column(default=0.0)
    provider_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    render_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    render_finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    project: Mapped[Project] = relationship("Project", back_populates="shots")


class StylePack(Base):
    __tablename__ = "style_packs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    yaml_path: Mapped[str] = mapped_column(String(512), nullable=False)
    embedding_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_builtin: Mapped[bool] = mapped_column(default=False)


class RenderJob(Base):
    __tablename__ = "render_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    output_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    timeline_json: Mapped[dict[str, Any]] = mapped_column(SQLiteJSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running, done, failed
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    total_cost_usd: Mapped[float] = mapped_column(default=0.0)

    project: Mapped[Project] = relationship("Project", back_populates="renders")


class BrollClip(Base):
    __tablename__ = "broll_clips"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    shot_id: Mapped[str] = mapped_column(ForeignKey("shots.id"), nullable=False)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    prompt_text: Mapped[str] = mapped_column(String(2000), default="")
    clip_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, rendering, done, failed
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    cost_usd: Mapped[float] = mapped_column(default=0.0)
    provider_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration_sec: Mapped[float] = mapped_column(default=0.0)
    clip_meta: Mapped[dict[str, Any]] = mapped_column(SQLiteJSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    shot: Mapped[Shot] = relationship("Shot")
    project: Mapped[Project] = relationship("Project")


class ExportJob(Base):
    __tablename__ = "export_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # mp4, archive, stills, edl
    status: Mapped[str] = mapped_column(String(20), default="queued")  # queued, processing, completed, failed
    progress: Mapped[float] = mapped_column(default=0.0)
    output_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    output_size: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    project: Mapped[Project] = relationship("Project", back_populates="exports")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db(database_url: str) -> None:
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
