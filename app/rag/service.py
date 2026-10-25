from __future__ import annotations

import uuid

from app.models.knowledge_chunk import KnowledgeChunk
from app.rag.chunking import chunk_text
from app.rag.embeddings import EmbeddingProvider
from app.rag.retrieval import RetrievedChunk, top_k
from app.repositories.knowledge_chunk import KnowledgeChunkRepository


class RagService:
    def __init__(
        self, *, embedder: EmbeddingProvider, chunk_repo: KnowledgeChunkRepository
    ) -> None:
        self.embedder = embedder
        self.chunk_repo = chunk_repo

    async def ingest_source(
        self,
        *,
        scenario_id: uuid.UUID,
        source_url: str,
        source_title: str,
        source_type: str,
        content: str,
        max_chars: int = 800,
    ) -> list[KnowledgeChunk]:
        chunks = chunk_text(content, max_chars=max_chars)
        if not chunks:
            return []
        vectors = self.embedder.embed_batch([c.text for c in chunks])
        models = [
            KnowledgeChunk(
                scenario_id=scenario_id,
                source_url=source_url,
                source_title=source_title,
                source_type=source_type,
                chunk_index=c.index,
                content=c.text,
                embedding=vec,
                meta={},
            )
            for c, vec in zip(chunks, vectors)
        ]
        await self.chunk_repo.add_many(models)
        return models

    async def retrieve(
        self, *, scenario_id: uuid.UUID, query: str, k: int = 5
    ) -> list[RetrievedChunk]:
        chunks = await self.chunk_repo.list_by_scenario(scenario_id)
        query_vec = self.embedder.embed(query)
        return top_k(query_vec, chunks, k=k)