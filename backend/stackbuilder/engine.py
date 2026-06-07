"""StackBuilder engine — scores routing profiles against project constraints.

The most robust logic in the app. Given project metadata (topic, duration,
hardware, budget, deadline), returns ranked profile recommendations.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from backend.stackbuilder.profiles import PROFILE_TRADEOFFS, ProfileTradeoffs

logger = logging.getLogger(__name__)


@dataclass
class ProjectConstraints:
    """User-declared or inferred project constraints."""
    topic: str = "documentary"           # documentary, explainer, archival, news, cinematic, research
    target_duration_min: float = 1.0     # minutes
    budget_usd: float = 5.00
    deadline_hours: float = 24.0
    vram_available_gb: int = 0           # 0 = no GPU / cloud only
    prioritize: str = "balanced"         # quality, speed, cost, depth, balanced
    source_count: int = 1                # number of uploaded documents
    word_count: int = 0                  # total source text length


@dataclass
class ProfileScore:
    """Scored result for a single profile."""
    name: str
    tradeoffs: ProfileTradeoffs
    overall_score: float
    dimension_scores: dict[str, float]
    recommendation: str                # "strong_match", "viable", "not_recommended"
    warnings: list[str]


class StackBuilder:
    """Intelligent profile selector for CineForge projects."""

    # Weight presets by prioritize mode
    WEIGHTS: dict[str, dict[str, float]] = {
        "quality":   {"quality": 0.40, "speed": 0.10, "cost": 0.10, "depth": 0.25, "compat": 0.15},
        "speed":     {"quality": 0.15, "speed": 0.40, "cost": 0.15, "depth": 0.10, "compat": 0.20},
        "cost":      {"quality": 0.10, "speed": 0.10, "cost": 0.40, "depth": 0.20, "compat": 0.20},
        "depth":     {"quality": 0.20, "speed": 0.05, "cost": 0.15, "depth": 0.45, "compat": 0.15},
        "balanced":  {"quality": 0.25, "speed": 0.20, "cost": 0.20, "depth": 0.20, "compat": 0.15},
    }

    # Topic → default style pack mapping
    TOPIC_STYLES: dict[str, str] = {
        "documentary": "documentary_natural",
        "explainer": "whiteboard_explainer",
        "archival": "archival_sepia",
        "news": "documentary_natural",
        "cinematic": "cinematic_noir",
        "research": "whiteboard_explainer",
        "tutorial": "whiteboard_explainer",
        "historical": "archival_sepia",
    }

    # Topic → default grammar mapping
    TOPIC_GRAMMARS: dict[str, str] = {
        "documentary": "mini_doc",
        "explainer": "explainer_short",
        "archival": "mini_doc",
        "news": "explainer_short",
        "cinematic": "narrative_3_act",
        "research": "research_walkthrough",
        "tutorial": "research_walkthrough",
        "historical": "mini_doc",
    }

    # Topic → recommended profiles (ordered preference)
    TOPIC_PROFILES: dict[str, list[str]] = {
        "documentary": ["documentary_deep", "hybrid_balanced", "documentary_fast", "framepack_hybrid", "archival_premium"],
        "explainer": ["explainer_budget", "research_walkthrough", "hybrid_balanced", "documentary_fast"],
        "archival": ["archival_premium", "documentary_deep", "hybrid_balanced"],
        "news": ["news_breaking", "documentary_fast", "hybrid_balanced"],
        "cinematic": ["cloud_premium", "framepack_hybrid", "hybrid_balanced"],
        "research": ["research_walkthrough", "documentary_deep", "explainer_budget"],
        "tutorial": ["explainer_budget", "research_walkthrough", "documentary_fast"],
        "historical": ["archival_premium", "documentary_deep", "explainer_budget"],
    }

    def __init__(self) -> None:
        pass

    def recommend(self, constraints: ProjectConstraints) -> list[ProfileScore]:
        """Score all profiles against constraints, return ranked list."""
        weights = self.WEIGHTS.get(constraints.prioritize, self.WEIGHTS["balanced"])
        results: list[ProfileScore] = []

        for name, tradeoffs in PROFILE_TRADEOFFS.items():
            scores, warnings = self._score_dimensions(constraints, tradeoffs, weights)
            overall = sum(scores.values())

            # Determine recommendation tier
            if overall >= 0.75 and not warnings:
                rec = "strong_match"
            elif overall >= 0.50:
                rec = "viable"
            else:
                rec = "not_recommended"

            results.append(ProfileScore(
                name=name,
                tradeoffs=tradeoffs,
                overall_score=round(overall, 3),
                dimension_scores={k: round(v, 3) for k, v in scores.items()},
                recommendation=rec,
                warnings=warnings,
            ))

        # Sort by overall score descending
        results.sort(key=lambda x: x.overall_score, reverse=True)
        return results

    def _score_dimensions(
        self,
        c: ProjectConstraints,
        t: ProfileTradeoffs,
        w: dict[str, float],
    ) -> tuple[dict[str, float], list[str]]:
        """Score individual dimensions and collect warnings."""
        scores: dict[str, float] = {}
        warnings: list[str] = []

        # Quality dimension
        scores["quality"] = t.quality_score

        # Speed dimension — deadline pressure
        estimated_hours = self._estimate_hours(c, t)
        if estimated_hours <= c.deadline_hours * 0.5:
            scores["speed"] = t.speed_score * 1.2  # Bonus for comfortable margin
        elif estimated_hours <= c.deadline_hours:
            scores["speed"] = t.speed_score
        else:
            scores["speed"] = t.speed_score * 0.5
            warnings.append(f"Estimated {estimated_hours:.1f}h exceeds {c.deadline_hours}h deadline")

        # Cost dimension — budget fit
        estimated_cost = self._estimate_cost(c, t)
        if estimated_cost <= c.budget_usd * 0.5:
            scores["cost"] = t.cost_score * 1.2
        elif estimated_cost <= c.budget_usd:
            scores["cost"] = t.cost_score
        else:
            scores["cost"] = t.cost_score * 0.3
            warnings.append(f"Estimated ${estimated_cost:.2f} exceeds ${c.budget_usd:.2f} budget")

        # Depth dimension — topic complexity
        depth_need = self._depth_need(c)
        scores["depth"] = 1.0 - abs(t.depth_score - depth_need)

        # Compatibility dimension — hardware & duration
        scores["compat"] = 1.0
        if c.vram_available_gb > 0 and t.vram_required_gb > c.vram_available_gb:
            scores["compat"] *= 0.3
            warnings.append(f"Requires {t.vram_required_gb}GB VRAM, only {c.vram_available_gb}GB available")
        elif c.vram_available_gb == 0 and t.local_dependency > 0.5:
            scores["compat"] *= 0.2
            warnings.append("No GPU detected but profile requires local inference")

        if c.target_duration_min > t.max_recommended_duration_min:
            scores["compat"] *= 0.7
            warnings.append(f"Duration {c.target_duration_min}min exceeds recommended {t.max_recommended_duration_min}min")

        # Apply weights
        weighted = {
            "quality": scores["quality"] * w["quality"],
            "speed": scores["speed"] * w["speed"],
            "cost": scores["cost"] * w["cost"],
            "depth": scores["depth"] * w["depth"],
            "compat": scores["compat"] * w["compat"],
        }
        return weighted, warnings

    def _estimate_hours(self, c: ProjectConstraints, t: ProfileTradeoffs) -> float:
        """Rough time estimate: treatment + storyboard + render + post-process."""
        llm_time = 0.1 if t.local_dependency < 0.5 else 0.5  # cloud LLM fast, local slow
        video_time = c.target_duration_min * 2.0 * (1.5 - t.speed_score)  # slower = more time per minute
        post_time = c.target_duration_min * 0.3 if t.local_dependency > 0.5 else 0
        return llm_time + video_time + post_time

    def _estimate_cost(self, c: ProjectConstraints, t: ProfileTradeoffs) -> float:
        """Rough cost estimate in USD."""
        llm_cost = 0.50 if t.local_dependency < 0.5 else 0.0
        # cost_score is inverse cost (higher = cheaper), so convert to a direct cost factor.
        cost_factor = 1.0 - t.cost_score
        video_cost = c.target_duration_min * 60 * cost_factor * 0.10  # rough $/sec proxy
        return llm_cost + video_cost

    def _depth_need(self, c: ProjectConstraints) -> float:
        """How much narrative depth does this project need?"""
        base_depth = 0.5
        if c.source_count > 3:
            base_depth += 0.15
        if c.word_count > 5000:
            base_depth += 0.15
        if c.topic in {"research", "documentary", "archival", "historical"}:
            base_depth += 0.20
        if c.target_duration_min > 5:
            base_depth += 0.10
        return min(base_depth, 1.0)

    def get_defaults(self, topic: str) -> dict[str, Any]:
        """Return default style pack and grammar for a topic."""
        return {
            "style_pack": self.TOPIC_STYLES.get(topic, "documentary_natural"),
            "grammar": self.TOPIC_GRAMMARS.get(topic, "mini_doc"),
            "recommended_profiles": self.TOPIC_PROFILES.get(topic, ["hybrid_balanced"]),
        }
