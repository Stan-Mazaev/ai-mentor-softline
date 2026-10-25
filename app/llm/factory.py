from functools import lru_cache

from app.core.config import get_settings
from app.llm.cache import TTLCache
from app.llm.circuit_breaker import CircuitBreaker
from app.llm.gateway import LLMGateway
from app.llm.stub import StubLLMProvider


@lru_cache
def get_llm_gateway() -> LLMGateway:
    settings = get_settings()
    return LLMGateway(
        provider=StubLLMProvider(),
        cache=TTLCache(ttl_seconds=settings.llm_cache_ttl),
        breaker=CircuitBreaker(
            failure_threshold=settings.llm_circuit_failure_threshold,
            reset_timeout=settings.llm_circuit_reset_seconds,
        ),
    )