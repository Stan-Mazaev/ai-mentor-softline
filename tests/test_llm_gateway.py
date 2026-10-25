from app.llm.base import LLMRequest, LLMResponse
from app.llm.cache import TTLCache
from app.llm.circuit_breaker import CircuitBreaker
from app.llm.gateway import LLMGateway


class _CountingProvider:
    name = "counting"
    model = "counting-1"

    def __init__(self, *, fail: bool = False) -> None:
        self.calls = 0
        self.fail = fail

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls += 1
        if self.fail:
            raise RuntimeError("provider is down")
        return LLMResponse(text="ok", model=self.model, tokens_in=1, tokens_out=1)


class _StubFallback:
    name = "stub"
    model = "stub-1"

    def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(text="fallback", model="stub-1", tokens_in=1, tokens_out=1)


def test_cache_hits_do_not_call_provider():
    provider = _CountingProvider()
    gw = LLMGateway(
        provider=provider,
        cache=TTLCache(ttl_seconds=60),
        breaker=CircuitBreaker(failure_threshold=3, reset_timeout=10),
    )
    req = LLMRequest(prompt="hello", task="info")
    a = gw.generate(req)
    b = gw.generate(req)
    assert provider.calls == 1
    assert b.cached is True
    assert a.text == b.text


def test_circuit_open_uses_fallback():
    provider = _CountingProvider(fail=True)
    gw = LLMGateway(
        provider=provider,
        cache=TTLCache(ttl_seconds=60),
        breaker=CircuitBreaker(failure_threshold=1, reset_timeout=60),
        fallback=_StubFallback(),
    )
    resp = gw.generate(LLMRequest(prompt="x", task="feedback"))
    assert resp.text == "fallback"
    assert gw.stats.provider_errors == 1 or gw.stats.circuit_fallbacks == 1