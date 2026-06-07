"""LiteLLM-backed LLM director adapter."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from backend.adapters.protocols import LLMCapabilities, LLMRequest, LLMResponse, LLMUsage

logger = logging.getLogger(__name__)


class LiteLLMDirector:
    """Wraps litellm.acompletion with structured output and caching."""

    def __init__(self) -> None:
        self.capabilities = LLMCapabilities(
            provider_id="litellm",
            display_name="LiteLLM Gateway",
            context_window=200_000,
            supports_prompt_caching=True,
            supports_structured_output=True,
            supports_tool_use=True,
            is_local=False,
            cost_per_1k_input_usd=0.003,
            cost_per_1k_output_usd=0.015,
            cost_per_1k_cached_input_usd=0.0003,
        )
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import litellm

                litellm.set_verbose = False  # type: ignore[attr-defined]
                self._client = litellm
            except ImportError:
                raise RuntimeError("litellm not installed")
        return self._client

    async def complete(self, req: LLMRequest) -> LLMResponse:
        client = self._get_client()
        model = os.getenv("LITELLM_PROVIDER", "anthropic/claude-sonnet-4-6")

        messages: list[dict[str, Any]] = [{"role": "system", "content": req.system}]
        messages.extend(req.messages)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
        }

        if req.response_schema:
            kwargs["response_format"] = {
                "type": "json_object",
                "schema": req.response_schema,
            }

        if req.tools:
            kwargs["tools"] = req.tools

        try:
            response = await client.acompletion(**kwargs)
        except Exception as exc:
            logger.error("LiteLLM completion failed: %s", exc)
            raise

        content = response.choices[0].message.content
        # If structured output requested, attempt parse
        if req.response_schema and isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                pass

        usage_raw = response.get("usage", {})
        usage = LLMUsage(
            input_tokens=usage_raw.get("prompt_tokens", 0),
            output_tokens=usage_raw.get("completion_tokens", 0),
            cached_input_tokens=usage_raw.get("prompt_cache_hit_tokens", 0),
            cost_usd=self._estimate_cost(usage_raw, model),
        )

        return LLMResponse(
            content=content,
            usage=usage,
            provider_id=self.capabilities.provider_id,
        )

    def _estimate_cost(self, usage_raw: dict[str, Any], model: str) -> float:
        inp: int = usage_raw.get("prompt_tokens", 0)
        out: int = usage_raw.get("completion_tokens", 0)
        cached: int = usage_raw.get("prompt_cache_hit_tokens", 0)
        # Use declared costs; override with env if needed
        cost = (
            (inp - cached) * self.capabilities.cost_per_1k_input_usd / 1000
            + out * self.capabilities.cost_per_1k_output_usd / 1000
            + cached * self.capabilities.cost_per_1k_cached_input_usd / 1000
        )
        return round(cost, 6)

    async def healthcheck(self) -> bool:
        try:
            client = self._get_client()
            # Lightweight call
            await client.acompletion(
                model=os.getenv("LITELLM_PROVIDER", "anthropic/claude-haiku-4-5"),
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
            )
            return True
        except Exception:
            return False
