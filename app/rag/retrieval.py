from __future__ import annotations

import math
from dataclasses import dataclass

from app.models.knowledge_chunk import KnowledgeChunk


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: KnowledgeChunk
    score: float


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def top_k(
    query_vec: list[float], chunks: list[KnowledgeChunk], *, k: int = 5
) -> list[RetrievedChunk]:
    scored: list[RetrievedChunk] = []
    for chunk in chunks:
        if not chunk.embedding:
            continue
        scored.append(RetrievedChunk(chunk=chunk, score=cosine(query_vec, chunk.embedding)))
    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:k]