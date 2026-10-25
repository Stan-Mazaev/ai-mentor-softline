import pytest

from app.llm.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState


class _Clock:
    def __init__(self) -> None:
        self.t = 0.0
    def __call__(self) -> float:
        return self.t
    def advance(self, dt: float) -> None:
        self.t += dt


def test_opens_after_threshold_failures():
    clock = _Clock()
    cb = CircuitBreaker(failure_threshold=2, reset_timeout=10.0, clock=clock)

    def boom():
        raise RuntimeError("boom")

    for _ in range(2):
        with pytest.raises(RuntimeError):
            cb.call(boom)

    assert cb.state == CircuitState.OPEN
    with pytest.raises(CircuitOpenError):
        cb.call(lambda: "ok")


def test_recovers_to_half_open_after_timeout():
    clock = _Clock()
    cb = CircuitBreaker(failure_threshold=1, reset_timeout=5.0, clock=clock)

    with pytest.raises(RuntimeError):
        cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))

    assert cb.state == CircuitState.OPEN
    clock.advance(6.0)
    assert cb.state == CircuitState.HALF_OPEN

    assert cb.call(lambda: "ok") == "ok"
    assert cb.state == CircuitState.CLOSED


def test_success_resets_failures():
    cb = CircuitBreaker(failure_threshold=3, reset_timeout=10.0)
    with pytest.raises(RuntimeError):
        cb.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    assert cb.failures == 1
    assert cb.call(lambda: "ok") == "ok"
    assert cb.failures == 0