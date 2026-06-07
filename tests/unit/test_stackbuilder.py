"""Unit tests for StackBuilder engine and profile scoring."""
import pytest

from backend.stackbuilder.engine import StackBuilder, ProjectConstraints
from backend.stackbuilder.profiles import PROFILE_TRADEOFFS


class TestProfileTradeoffs:
    def test_all_profiles_have_required_fields(self):
        for name, tradeoffs in PROFILE_TRADEOFFS.items():
            assert 0.0 <= tradeoffs.quality_score <= 1.0
            assert 0.0 <= tradeoffs.speed_score <= 1.0
            assert 0.0 <= tradeoffs.cost_score <= 1.0
            assert 0.0 <= tradeoffs.depth_score <= 1.0
            assert 0.0 <= tradeoffs.local_dependency <= 1.0
            assert tradeoffs.vram_required_gb >= 0
            assert tradeoffs.max_recommended_duration_min > 0
            assert tradeoffs.primary_use_case
            assert tradeoffs.description

    def test_budget_local_is_max_cost(self):
        t = PROFILE_TRADEOFFS["budget_local"]
        assert t.cost_score == 1.0
        assert t.local_dependency == 1.0

    def test_cloud_premium_is_max_quality(self):
        t = PROFILE_TRADEOFFS["cloud_premium"]
        assert t.quality_score >= 0.90
        assert t.local_dependency == 0.0

    def test_documentary_profiles_exist(self):
        assert "documentary_fast" in PROFILE_TRADEOFFS
        assert "documentary_deep" in PROFILE_TRADEOFFS
        assert "explainer_budget" in PROFILE_TRADEOFFS
        assert "archival_premium" in PROFILE_TRADEOFFS
        assert "research_walkthrough" in PROFILE_TRADEOFFS
        assert "news_breaking" in PROFILE_TRADEOFFS


class TestStackBuilderRecommend:
    def test_recommend_returns_ranked_list(self):
        builder = StackBuilder()
        constraints = ProjectConstraints(
            topic="documentary",
            target_duration_min=5,
            budget_usd=10,
            deadline_hours=24,
            vram_available_gb=8,
            prioritize="balanced",
        )
        scores = builder.recommend(constraints)
        assert len(scores) == len(PROFILE_TRADEOFFS)
        # Should be sorted descending
        for i in range(len(scores) - 1):
            assert scores[i].overall_score >= scores[i + 1].overall_score

    def test_strong_match_for_appropriate_hardware(self):
        builder = StackBuilder()
        constraints = ProjectConstraints(
            topic="documentary",
            target_duration_min=3,
            budget_usd=5,
            deadline_hours=12,
            vram_available_gb=12,
            prioritize="balanced",
        )
        scores = builder.recommend(constraints)
        top = scores[0]
        assert top.recommendation in {"strong_match", "viable"}

    def test_warns_on_insufficient_vram(self):
        builder = StackBuilder()
        constraints = ProjectConstraints(
            topic="documentary",
            target_duration_min=10,
            budget_usd=5,
            deadline_hours=24,
            vram_available_gb=2,  # too low for most local
            prioritize="balanced",
        )
        scores = builder.recommend(constraints)
        # At least one profile should warn about VRAM
        warnings = [w for s in scores for w in s.warnings]
        assert any("VRAM" in w for w in warnings)

    def test_warns_on_tight_deadline(self):
        builder = StackBuilder()
        constraints = ProjectConstraints(
            topic="news",
            target_duration_min=5,
            budget_usd=50,
            deadline_hours=0.5,  # 30 minutes
            vram_available_gb=0,
            prioritize="speed",
        )
        scores = builder.recommend(constraints)
        # news_breaking or cloud_premium should be top
        assert scores[0].name in {"news_breaking", "cloud_premium", "documentary_fast"}

    def test_cost_prioritization_favors_free(self):
        builder = StackBuilder()
        constraints = ProjectConstraints(
            topic="explainer",
            target_duration_min=3,
            budget_usd=0,
            deadline_hours=48,
            vram_available_gb=8,
            prioritize="cost",
        )
        scores = builder.recommend(constraints)
        top = scores[0]
        assert top.tradeoffs.cost_score >= 0.90

    def test_depth_prioritization_favors_documentary_deep(self):
        builder = StackBuilder()
        constraints = ProjectConstraints(
            topic="documentary",
            target_duration_min=10,
            budget_usd=20,
            deadline_hours=48,
            vram_available_gb=12,
            prioritize="depth",
            source_count=5,
            word_count=10000,
        )
        scores = builder.recommend(constraints)
        # documentary_deep should be in top 3
        names = [s.name for s in scores[:3]]
        assert "documentary_deep" in names

    def test_topic_defaults(self):
        builder = StackBuilder()
        defaults = builder.get_defaults("research")
        assert defaults["style_pack"] == "whiteboard_explainer"
        assert defaults["grammar"] == "research_walkthrough"
        assert "research_walkthrough" in defaults["recommended_profiles"]

    def test_documentary_defaults(self):
        builder = StackBuilder()
        defaults = builder.get_defaults("documentary")
        assert defaults["style_pack"] == "documentary_natural"
        assert defaults["grammar"] == "mini_doc"

    def test_cinematic_defaults(self):
        builder = StackBuilder()
        defaults = builder.get_defaults("cinematic")
        assert defaults["style_pack"] == "cinematic_noir"
        assert defaults["grammar"] == "narrative_3_act"

    def test_estimate_hours_reasonable(self):
        builder = StackBuilder()
        c = ProjectConstraints(target_duration_min=5)
        t = PROFILE_TRADEOFFS["cloud_premium"]
        hours = builder._estimate_hours(c, t)
        assert 0 < hours < 24

    def test_estimate_cost_cloud_has_llm_cost(self):
        builder = StackBuilder()
        c = ProjectConstraints(target_duration_min=3)
        t = PROFILE_TRADEOFFS["cloud_premium"]
        cost = builder._estimate_cost(c, t)
        assert cost > 0  # cloud has LLM cost

    def test_estimate_cost_local_is_zero(self):
        builder = StackBuilder()
        c = ProjectConstraints(target_duration_min=3)
        t = PROFILE_TRADEOFFS["budget_local"]
        cost = builder._estimate_cost(c, t)
        assert cost == 0.0
