import uuid

from app.rag.embeddings import HashingEmbeddingProvider
from app.rag.service import RagService
from app.repositories.knowledge_chunk import KnowledgeChunkRepository
from app.repositories.scenario import ScenarioRepository


async def test_ingest_and_retrieve(db_session):
    scenario = await ScenarioRepository(db_session).create(
        slug="university_choice", title="Выбор вуза"
    )
    rag = RagService(
        embedder=HashingEmbeddingProvider(dim=256),
        chunk_repo=KnowledgeChunkRepository(db_session),
    )

    await rag.ingest_source(
        scenario_id=scenario.id,
        source_url="https://a",
        source_title="Приём",
        source_type="official",
        content="Приём документов открывается 20 июня. Нужны результаты ЕГЭ.",
    )
    await rag.ingest_source(
        scenario_id=scenario.id,
        source_url="https://b",
        source_title="Онбординг",
        source_type="open",
        content="В первый месяц важно задавать вопросы и читать документацию.",
    )

    hits = await rag.retrieve(scenario_id=scenario.id, query="когда открывается приём и ЕГЭ", k=2)
    assert len(hits) == 2
    assert hits[0].chunk.source_url == "https://a"
    assert hits[0].score > hits[1].score