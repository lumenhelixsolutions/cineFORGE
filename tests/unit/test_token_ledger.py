"""Unit tests for TokenLedger modules."""
import pytest

from backend.token_ledger.router import RoutingConfig
from backend.token_ledger.cache import PromptCache
from backend.token_ledger.semantic import SemanticCache
from backend.token_ledger.counter import TokenCounter
from backend.adapters.protocols import LLMUsage


class TestRoutingConfig:
    def test_from_file_creates_default(self, tmp_path):
        path = tmp_path / 'routing.yaml'
        config = RoutingConfig.from_file(path)
        assert 'profiles' in config.config
        assert 'cloud_premium' in config.profiles
        assert 'local_two_stage' in config.profiles
        assert 'hybrid' in config.profiles

    def test_resolve_llm(self, tmp_path):
        path = tmp_path / 'routing.yaml'
        config = RoutingConfig.from_file(path)
        assert config.resolve_llm('treatment', 'cloud_premium') == 'anthropic.claude-sonnet-4-6'
        assert config.resolve_llm('fallback', 'cloud_premium') == 'gemini.gemini-2.5-flash'

    def test_resolve_video(self, tmp_path):
        path = tmp_path / 'routing.yaml'
        config = RoutingConfig.from_file(path)
        assert config.resolve_video('hero', 'cloud_premium') == 'vertex.veo-3.1'
        assert config.resolve_video('broll', 'cloud_premium') == 'fal.hailuo-02'

    def test_preview_mode(self, tmp_path):
        path = tmp_path / 'routing.yaml'
        config = RoutingConfig.from_file(path)
        assert config.resolve_video('hero', 'hybrid', preview_mode=True) == 'wan2gp.ltx-video-2.3'

    def test_update_and_save(self, tmp_path):
        path = tmp_path / 'routing.yaml'
        config = RoutingConfig.from_file(path)
        config.update({'profiles': {'test': {'llm': {'treatment': 'test.model'}}}})
        config.save(path)
        reloaded = RoutingConfig.from_file(path)
        assert 'test' in reloaded.profiles


class TestPromptCache:
    def test_cache_hit(self):
        cache = PromptCache()
        system = "You are a director"
        messages = [{"role": "user", "content": "test"}]
        cache.set(system, messages, None, {"result": "ok"})
        result = cache.get(system, messages, None)
        assert result == {"result": "ok"}

    def test_cache_miss(self):
        cache = PromptCache()
        result = cache.get("system", [{"role": "user", "content": "test"}], None)
        assert result is None

    def test_hit_rate(self):
        cache = PromptCache()
        cache.set("s1", [{"role": "user", "content": "a"}], None, "r1")
        cache.set("s2", [{"role": "user", "content": "b"}], None, "r2")
        cache.get("s1", [{"role": "user", "content": "a"}], None)
        cache.get("s1", [{"role": "user", "content": "a"}], None)
        assert cache.hit_rate() == 0.5


class TestSemanticCache:
    def test_cosine_similarity(self, tmp_path):
        cache = SemanticCache(tmp_path, dim=3)
        a = [1.0, 0.0, 0.0]
        b = [0.9, 0.1, 0.0]
        sim = cache._cosine(a, b)
        assert 0.9 < sim <= 1.0

    def test_different_vectors_low_sim(self, tmp_path):
        cache = SemanticCache(tmp_path, dim=3)
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        sim = cache._cosine(a, b)
        assert sim == 0.0


class TestTokenCounter:
    def test_add_usage(self):
        counter = TokenCounter(budget_usd=1.00)
        usage = LLMUsage(input_tokens=1000, output_tokens=500, cached_input_tokens=200, cost_usd=0.015)
        counter.add(usage)
        assert counter.total_input == 1000
        assert counter.total_output == 500
        assert counter.total_cached == 200

    def test_check_budget(self):
        counter = TokenCounter(budget_usd=0.10)
        counter.add(LLMUsage(input_tokens=1000, output_tokens=500, cost_usd=0.08))
        assert counter.check_budget(0.01) is True
        assert counter.check_budget(0.03) is False

    def test_report(self):
        counter = TokenCounter(budget_usd=1.00)
        counter.add(LLMUsage(input_tokens=1000, output_tokens=0, cached_input_tokens=800, cost_usd=0.01))
        report = counter.report()
        assert report['cache_hit_rate'] == 0.8
        assert report['remaining_budget_usd'] == 0.99
