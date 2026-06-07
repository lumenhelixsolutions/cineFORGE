"""Token usage metering and budget enforcement."""

from __future__ import annotations

import logging
from typing import Any

from backend.adapters.protocols import LLMUsage

logger = logging.getLogger(__name__)


class TokenCounter:
    """Tracks cumulative token usage and enforces per-project budgets."""

    def __init__(self, budget_usd: float = 1.00) -> None:
        self.budget_usd = budget_usd
        self.total_input = 0
        self.total_output = 0
        self.total_cached = 0
        self.total_cost = 0.0

    def add(self, usage: LLMUsage) -> None:
        self.total_input += usage.input_tokens
        self.total_output += usage.output_tokens
        self.total_cached += usage.cached_input_tokens
        self.total_cost += usage.cost_usd
        logger.info(
            "Tokens: +%d in / +%d out / +%d cached | cost $%.4f | total $%.4f",
            usage.input_tokens,
            usage.output_tokens,
            usage.cached_input_tokens,
            usage.cost_usd,
            self.total_cost,
        )

    def check_budget(self, projected_cost: float) -> bool:
        """Return True if projected cost stays within budget."""
        if self.total_cost + projected_cost > self.budget_usd:
            logger.warning("Budget exceeded: $%.4f + $%.4f > $%.4f", self.total_cost, projected_cost, self.budget_usd)
            return False
        return True

    def report(self) -> dict[str, Any]:
        total = self.total_input + self.total_output
        cache_rate = self.total_cached / max(self.total_input, 1)
        return {
            "input_tokens": self.total_input,
            "output_tokens": self.total_output,
            "cached_input_tokens": self.total_cached,
            "total_tokens": total,
            "cache_hit_rate": round(cache_rate, 3),
            "total_cost_usd": round(self.total_cost, 4),
            "budget_usd": self.budget_usd,
            "remaining_budget_usd": round(self.budget_usd - self.total_cost, 4),
        }
