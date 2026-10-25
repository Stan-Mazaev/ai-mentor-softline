import uuid

import pytest

from app.dialog.schemas import SessionCreate
from app.dialog.service import DialogError, DialogService
from app.dialog.states import DialogMode
from app.guardrails.pii import mask_pii
from app.llm.cache import TTLCache
from app.llm.circuit_breaker import CircuitBreaker
from app.llm.gateway import LLMGateway
from app.llm.stub import StubLLMProvider
from app.rag.embeddings import HashingEmbeddingProvider
from app.rag.service import RagService
from app.repositories.knowledge_chunk import KnowledgeChunkRepository
from app.repositories.scenario import ScenarioRepository


def _llm() -> LLMGateway:
    return LLMGateway(
        provider=StubLLMProvider(),
        cache=TTLCache(ttl_seconds=60),
        breaker=CircuitBreaker(failure_threshold=3, reset_timeout=10),
    )


async def _seed_scenario(db_session, slug: str) -> None:
    repo = ScenarioRepository(db_session)
    scenario = await repo.create(slug=slug, title=slug)
    rag = RagService(
        embedder=HashingEmbeddingProvider(dim=128),
        chunk_repo=KnowledgeChunkRepository(db_session),
    )
    await rag.ingest_source(
        scenario_id=scenario.id,
        source_url="https://example",
        source_title="Пример",
        source_type="open",
        content="Приём документов открывается 20 июня. Нужны результаты ЕГЭ.",
    )


async def test_info_session_returns_answer_with_citations(db_session):
    await _seed_scenario(db_session, "university_choice")
    service = DialogService(session=db_session, llm=_llm())

    s = await service.create_session(
        scenario_slug="university_choice", mode=DialogMode.INFO, anonymous_id=None
    )
    assert s.state == "info_ready"

    resp = await service.post_message(session_id=s.id, content="когда подавать документы?")
    assert resp.state == "info_ready"
    assert resp.content
    assert resp.citations and len(resp.citations) >= 1
    assert resp.disclaimer is not None


async def test_trainer_session_flow(db_session):
    await _seed_scenario(db_session, "university_choice")
    service = DialogService(session=db_session, llm=_llm())

    s = await service.create_session(
        scenario_slug="university_choice", mode=DialogMode.TRAINER, anonymous_id="anon-1"
    )
    assert s.state == "awaiting_answer"
    assert s.initial_message

    resp1 = await service.post_message(session_id=s.id, content="Я не знаю, ничего не умею")
    assert resp1.evaluation is not None
    assert resp1.evaluation.verdict in {"needs_improvement", "incomplete"}

    resp2 = await service.post_message(session_id=s.id, content="Учту учебный план, практику и аккредитацию")
    assert resp2.evaluation is not None


async def test_unknown_scenario_404(db_session):
    service = DialogService(session=db_session, llm=_llm())
    with pytest.raises(DialogError) as exc:
        await service.create_session(
            scenario_slug="unknown", mode=DialogMode.INFO, anonymous_id=None
        )
    assert exc.value.status == 404