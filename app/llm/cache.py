from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable

from app.llm.base import LLMResponse


@dataclass
class _Entry:
    value: LLMResponse
    expires_at: float


class TTLCache:
    def __init__(
        self,
        *,
        ttl_seconds: float,
        max_size: int = 1024,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        self._ttl = ttl_seconds
        self._max = max_size
        self._clock = clock
        self._data: OrderedDict[str, _Entry] = OrderedDict()

    def get(self, key: str) -> LLMResponse | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        if entry.expires_at < self._clock():
            self._data.pop(key, None)
            return None
        self._data.move_to_end(key)
        return entry.value

    def set(self, key: str, value: LLMResponse) -> None:
        self._data[key] = _Entry(value=value, expires_at=self._clock() + self._ttl)
        self._data.move_to_end(key)
        while len(self._data) > self._max:
            self._data.popitem(last=False)

    def clear(self) -> None:
        self._data.clear()

    def __len__(self) -> int:
        return len(self._data)