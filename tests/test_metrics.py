from app.llm.base import LLMRequest
from app.llm.cache import TTLCache
from app.llm.circuit_breaker import CircuitBreaker
from app.llm.gateway import LLMGateway
from app.llm.stub import StubLLMProvider


def test_gateway_records_metrics_without_crash():
    gw = LLMGateway(
        provider=StubLLMProvider(),
        cache=TTLCache(ttl_seconds=60),
        breaker=CircuitBreaker(failure_threshold=3, reset_timeout=10),
    )
    gw.generate(LLMRequest(prompt="hello", task="info"))
    gw.generate(LLMRequest(prompt="hello", task="info"))
    assert gw.stats.requests_total == 2
    assert gw.stats.cache_hits == 1