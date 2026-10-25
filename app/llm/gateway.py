from __future__ import annotations

import hashlib
import json
import time  # <-- Добавлен импорт time
from dataclasses import dataclass, replace

from app.llm.base import LLMProvider, LLMRequest, LLMResponse
from app.llm.cache import TTLCache
from app.llm.circuit_breaker import CircuitBreaker, CircuitOpenError
from app.llm.stub import StubLLMProvider
from app.observability.metrics import LLM_LATENCY, LLM_REQUESTS, LLM_TOKENS  # <-- Добавлены метрики


@dataclass
class GatewayStats:
    requests_total: int = 0
    cache_hits: int = 0
    circuit_fallbacks: int = 0
    provider_errors: int = 0


class LLMGateway:
    """Обёртка над LLMProvider: кэш + Circuit Breaker + fallback + учёт токенов."""

    def __init__(
        self,
        *,
        provider: LLMProvider,
        cache: TTLCache,
        breaker: CircuitBreaker,
        fallback: LLMProvider | None = None,
    ) -> None:
        self._provider = provider
        self._cache = cache
        self._breaker = breaker
        self._fallback = fallback or StubLLMProvider()
        self._stats = GatewayStats()

    @property
    def stats(self) -> GatewayStats:
        return self._stats

    @property
    def breaker_state(self) -> str:
        return self._breaker.state.value

    def generate(self, request: LLMRequest) -> LLMResponse:
        self._stats.requests_total += 1
        key = self._cache_key(request)
        cached = self._cache.get(key)
        if cached is not None:
            self._stats.cache_hits += 1
            LLM_REQUESTS.labels(task=request.task, outcome="cache_hit").inc()
            return replace(cached, cached=True)

        start = time.perf_counter()
        try:
            response = self._breaker.call(self._provider.generate, request)
            outcome = "ok"
        except CircuitOpenError:
            self._stats.circuit_fallbacks += 1
            response = self._fallback.generate(request)
            outcome = "circuit_fallback"
        except Exception:
            self._stats.provider_errors += 1
            response = self._fallback.generate(request)
            outcome = "provider_error"
        finally:
            LLM_LATENCY.labels(task=request.task).observe(time.perf_counter() - start)

        LLM_REQUESTS.labels(task=request.task, outcome=outcome).inc()
        LLM_TOKENS.labels(direction="in").inc(response.tokens_in)
        LLM_TOKENS.labels(direction="out").inc(response.tokens_out)

        self._cache.set(key, response)
        return response

    @staticmethod
    def _cache_key(request: LLMRequest) -> str:
        payload = json.dumps(
            {
                "prompt": request.prompt,
                "task": request.task,
                "system": request.system,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()