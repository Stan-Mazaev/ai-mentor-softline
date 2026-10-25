from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.rag.embeddings import get_embedding_provider
from app.rag.service import RagService
from app.repositories.knowledge_chunk import KnowledgeChunkRepository
from app.repositories.scenario import ScenarioRepository
from app.schemas.rag import Citation, RagHit, RagSearchRequest, RagSearchResponse

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/search", response_model=RagSearchResponse)
async def search(
    payload: RagSearchRequest, session: AsyncSession = Depends(get_session)
) -> RagSearchResponse:
    scenario_repo = ScenarioRepository(session)
    scenario = await scenario_repo.get_by_slug(payload.scenario_slug)
    if scenario is None:
        raise HTTPException(status_code=404, detail="scenario not found")

    rag = RagService(
        embedder=get_embedding_provider(),
        chunk_repo=KnowledgeChunkRepository(session),
    )
    hits = await rag.retrieve(scenario_id=scenario.id, query=payload.query, k=payload.k)
    return RagSearchResponse(
        hits=[
            RagHit(
                content=h.chunk.content,
                score=round(h.score, 4),
                citation=Citation(
                    url=h.chunk.source_url,
                    title=h.chunk.source_title,
                    type=h.chunk.source_type,
                    chunk_index=h.chunk.chunk_index,
                ),
            )
            for h in hits
        ]
    )