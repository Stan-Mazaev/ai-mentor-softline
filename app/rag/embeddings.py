from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


class EmbeddingProvider(Protocol):
    dim: int

    def embed(self, text: str) -> list[float]: ...
    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


def _tokens(text: str) -> list[str]:
    """Слова + биграммы + символьные триграммы.

    Триграммы дают устойчивость к морфологии: "вуз"/"вуза",
    "рейтинг"/"рейтинги", "выбрать"/"выбор" делят общие подстроки
    и попадают в близкие бакеты.
    """
    text = text.lower()
    words = _TOKEN_RE.findall(text)
    bigrams = [f"{a}_{b}" for a, b in zip(words, words[1:])]
    trigrams: list[str] = []
    for w in words:
        if len(w) < 3:
            continue
        for i in range(len(w) - 2):
            trigrams.append(f"#{w[i:i + 3]}")
    return words + bigrams + trigrams


class HashingEmbeddingProvider:
    """Детерминированный локальный эмбеддер (hashing trick).

    Не семантический, но стабильный, без внешних зависимостей и numpy.
    Даёт приемлемое качество для dev/демо на небольшом корпусе.
    Реальный провайдер подключается через get_embedding_provider().
    """

    def __init__(self, dim: int = 256) -> None:
        if dim <= 0:
            raise ValueError("dim must be positive")
        self.dim = dim

    def _bucket(self, token: str) -> int:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big") % self.dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in _tokens(text):
            vec[self._bucket(token)] += 1.0
        norm = math.sqrt(sum(x * x for x in vec))
        if norm == 0:
            return vec
        return [x / norm for x in vec]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


def get_embedding_provider() -> EmbeddingProvider:
    return HashingEmbeddingProvider(dim=256)