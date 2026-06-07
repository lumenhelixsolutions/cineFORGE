"""StackBuilder profile definitions with explicit tradeoff dimensions.

Each profile declares its position on key axes so the StackBuilder can
score and rank options against project constraints.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class ProfileTradeoffs:
    """Quantified tradeoff positions for a routing profile."""
    quality_score: float          # 0.0–1.0, estimated output fidelity
    speed_score: float            # 0.0–1.0, generation throughput
    cost_score: float             # 0.0–1.0, $ per minute of output (inverse: higher = cheaper)
    depth_score: float            # 0.0–1.0, narrative complexity / research integration
    local_dependency: float       # 0.0–1.0, fraction of pipeline requiring local GPU
    vram_required_gb: int         # Minimum GPU VRAM, 0 = none needed
    max_recommended_duration_min: int
    primary_use_case: str
    description: str


PROFILE_TRADEOFFS: dict[str, ProfileTradeoffs] = {
    # ── Cloud-first ──────────────────────────────────────────
    "cloud_premium": ProfileTradeoffs(
        quality_score=0.95,
        speed_score=0.90,
        cost_score=0.15,
        depth_score=0.80,
        local_dependency=0.0,
        vram_required_gb=0,
        max_recommended_duration_min=10,
        primary_use_case="Premium documentary, cinematic archival, client delivery",
        description="Best quality, fastest turnaround, highest cost. Veo 3.1 + Claude. No GPU needed.",
    ),

    # ── Original hybrid ─────────────────────────────────────
    "hybrid": ProfileTradeoffs(
        quality_score=0.80,
        speed_score=0.70,
        cost_score=0.45,
        depth_score=0.70,
        local_dependency=0.30,
        vram_required_gb=6,
        max_recommended_duration_min=10,
        primary_use_case="General documentary, explainer, cost-conscious production",
        description="Local previews (free iteration) → cloud finals (quality). Balanced cost/speed.",
    ),

    # ── Research-based hybrids ──────────────────────────────
    "framepack_hybrid": ProfileTradeoffs(
        quality_score=0.75,
        speed_score=0.35,
        cost_score=0.70,
        depth_score=0.85,
        local_dependency=0.70,
        vram_required_gb=6,
        max_recommended_duration_min=10,
        primary_use_case="Long-form documentary, deep investigative pieces, narrative arcs",
        description="FramePack F1 for 60s+ continuous shots. Cloud LLM + local video + post-process.",
    ),

    "cogvideo_hybrid": ProfileTradeoffs(
        quality_score=0.55,
        speed_score=0.50,
        cost_score=0.75,
        depth_score=0.50,
        local_dependency=0.60,
        vram_required_gb=4,
        max_recommended_duration_min=3,
        primary_use_case="Short-form social, micro-documentary, laptop production",
        description="CogVideoX on 4GB VRAM. 6s micro-shots assembled into short videos.",
    ),

    "budget_local": ProfileTradeoffs(
        quality_score=0.60,
        speed_score=0.20,
        cost_score=1.00,
        depth_score=0.70,
        local_dependency=1.00,
        vram_required_gb=6,
        max_recommended_duration_min=10,
        primary_use_case="Zero-budget documentary, open-source education, privacy-critical work",
        description="100% free. Ollama + FramePack/CogVideoX + RIFE + Real-ESRGAN. No API keys.",
    ),

    # ── Documentary-focused new profiles ────────────────────
    "documentary_fast": ProfileTradeoffs(
        quality_score=0.65,
        speed_score=0.85,
        cost_score=0.55,
        depth_score=0.50,
        local_dependency=0.20,
        vram_required_gb=4,
        max_recommended_duration_min=5,
        primary_use_case="News reports, breaking documentary, rapid turnaround",
        description="Fastest documentary pipeline. Cloud LLM + CogVideoX + minimal post-process. Under 10 min total.",
    ),

    "documentary_deep": ProfileTradeoffs(
        quality_score=0.80,
        speed_score=0.30,
        cost_score=0.60,
        depth_score=0.95,
        local_dependency=0.60,
        vram_required_gb=8,
        max_recommended_duration_min=15,
        primary_use_case="Investigative journalism, long-form documentary, research synthesis",
        description="FramePack for extended scenes + cloud LLM for deep treatment + archival style packs. 3-act with 15+ beats.",
    ),

    "explainer_budget": ProfileTradeoffs(
        quality_score=0.50,
        speed_score=0.40,
        cost_score=1.00,
        depth_score=0.60,
        local_dependency=0.80,
        vram_required_gb=4,
        max_recommended_duration_min=5,
        primary_use_case="Educational content, tutorials, whiteboard explainers, non-profit",
        description="Zero-cost educational pipeline. Ollama + CogVideoX + whiteboard style + Piper narration.",
    ),

    "archival_premium": ProfileTradeoffs(
        quality_score=0.90,
        speed_score=0.60,
        cost_score=0.25,
        depth_score=0.85,
        local_dependency=0.10,
        vram_required_gb=0,
        max_recommended_duration_min=20,
        primary_use_case="Historical documentary, museum exhibits, premium archival",
        description="Maximum fidelity for archival work. Veo 3.1 + Claude + archival_sepia style + Real-ESRGAN upscale.",
    ),

    "research_walkthrough": ProfileTradeoffs(
        quality_score=0.70,
        speed_score=0.55,
        cost_score=0.50,
        depth_score=0.90,
        local_dependency=0.30,
        vram_required_gb=6,
        max_recommended_duration_min=8,
        primary_use_case="Academic papers, data visualization walkthrough, science communication",
        description="Equation reveals, diagram shots, derivation sequences. Whiteboard style + cloud LLM + FramePack for complex visuals.",
    ),

    "news_breaking": ProfileTradeoffs(
        quality_score=0.50,
        speed_score=0.95,
        cost_score=0.40,
        depth_score=0.30,
        local_dependency=0.0,
        vram_required_gb=0,
        max_recommended_duration_min=2,
        primary_use_case="Breaking news, social media clips, rapid response",
        description="Fastest possible. Cloud LLM + Veo Fast + no post-process. 2-minute turnaround for 60s video.",
    ),

    "hybrid_balanced": ProfileTradeoffs(
        quality_score=0.75,
        speed_score=0.65,
        cost_score=0.55,
        depth_score=0.75,
        local_dependency=0.40,
        vram_required_gb=6,
        max_recommended_duration_min=10,
        primary_use_case="General-purpose balanced production, adaptable to topic",
        description="Smart tiering: hero→Veo, standard→FramePack, broll→CogVideoX, title→LTX. Auto-selects based on shot complexity.",
    ),
}
