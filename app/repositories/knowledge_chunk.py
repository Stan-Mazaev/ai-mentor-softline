import uuid

from sqlalchemy import delete, select  # добавлен delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_chunk import KnowledgeChunk


class KnowledgeChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_many(self, chunks: list[KnowledgeChunk]) -> None:
        self.session.add_all(chunks)
        await self.session.commit()

    async def list_by_scenario(self, scenario_id: uuid.UUID) -> list[KnowledgeChunk]:
        result = await self.session.execute(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.scenario_id == scenario_id)
            .order_by(KnowledgeChunk.chunk_index)
        )
        return list(result.scalars().all())

    async def has_source(self, scenario_id: uuid.UUID, source_url: str) -> bool:
        result = await self.session.execute(
            select(KnowledgeChunk.id)
            .where(
                KnowledgeChunk.scenario_id == scenario_id,
                KnowledgeChunk.source_url == source_url,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def delete_by_source(self, scenario_id: uuid.UUID, source_url: str) -> int:
        result = await self.session.execute(
            delete(KnowledgeChunk).where(
                KnowledgeChunk.scenario_id == scenario_id,
                KnowledgeChunk.source_url == source_url,
            )
        )
        await self.session.commit()
        return result.rowcount or 0