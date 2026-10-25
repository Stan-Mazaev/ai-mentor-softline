from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dialog.adaptivity import record_weak_zone, reorder_cases_by_weak_zones
from app.dialog.cases import Case, load_cases
from app.dialog.evaluator import Evaluation, evaluate_answer
from app.dialog.machine import initial_state, on_user_message
from app.dialog.schemas import Citation, EvaluationOut, MessageOut, SessionOut
from app.dialog.states import DialogMode, DialogState
from app.guardrails.disclaimer import DISCLAIMER, with_disclaimer
from app.guardrails.pii import mask_pii
from app.llm import LLMGateway
from app.llm.base import LLMRequest
from app.models.dialog_session import DialogSession
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.scenario import Scenario
from app.models.turn import Turn
from app.models.user_profile import UserProfile
from app.rag.embeddings import get_embedding_provider
from app.rag.service import RagService
from app.repositories.knowledge_chunk import KnowledgeChunkRepository
from app.repositories.scenario import ScenarioRepository


class DialogError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


INFO_GREETING = (
    "Здравствуйте! Спросите что угодно про поступление, поиск первой работы "
    "или адаптацию в компании. Отвечу с опорой на источники."
)


class DialogService:
    def __init__(self, *, session: AsyncSession, llm: LLMGateway) -> None:
        self.session = session
        self.llm = llm
        self.scenario_repo = ScenarioRepository(session)
        self.chunk_repo = KnowledgeChunkRepository(session)

    # ---------- create ----------

    async def create_session(
            self, *, scenario_slug: str, mode: DialogMode, anonymous_id: str | None
    ) -> SessionOut:
        scenario = await self._require_scenario(scenario_slug)
        profile = await self._ensure_profile(anonymous_id)

        initial_message: str
        if mode == DialogMode.INFO:
            state = initial_state(mode)
            initial_message = INFO_GREETING
        else:
            cases = load_cases(scenario_slug)
            if not cases:
                raise DialogError(400, "no_cases", "no cases for scenario")

            # Адаптивная сортировка кейсов на основе прошлых ошибок пользователя
            cases = await reorder_cases_by_weak_zones(
                cases,
                profile_id=profile.id if profile else None,
                scenario_slug=scenario_slug,
                session=self.session,
            )
            state = initial_state(mode)
            initial_message = cases[0].question

        dialog = DialogSession(
            scenario_id=scenario.id,
            user_profile_id=profile.id if profile else None,
            mode=mode.value,
            state=state.value,
        )
        self.session.add(dialog)
        await self.session.flush()

        await self._save_turn(dialog.id, turn_index=0, role="assistant", content=initial_message)
        await self.session.commit()
        await self.session.refresh(dialog)

        return SessionOut(
            id=dialog.id,
            scenario_slug=scenario_slug,
            mode=dialog.mode,
            state=dialog.state,
            initial_message=initial_message,
        )

    # ---------- message ----------

    async def post_message(self, *, session_id: uuid.UUID, content: str) -> MessageOut:
        dialog = await self._require_session(session_id)
        mode = DialogMode(dialog.mode)
        state = DialogState(dialog.state)

        transition = on_user_message(state, mode)
        if not transition.allowed:
            raise DialogError(400, "invalid_state", f"cannot post message in state={state}")

        masked = mask_pii(content)
        next_index = await self._next_turn_index(dialog.id)
        await self._save_turn(dialog.id, turn_index=next_index, role="user", content=masked.text)

        if mode == DialogMode.INFO:
            response = await self._handle_info(dialog, masked.text, next_index + 1)
        else:
            response = await self._handle_trainer(dialog, masked.text, next_index + 1)

        await self.session.commit()
        return response

    # ---------- info branch ----------

    async def _handle_info(
            self, dialog: DialogSession, user_text: str, assistant_index: int
    ) -> MessageOut:
        scenario = await self.session.get(Scenario, dialog.scenario_id)
        assert scenario is not None

        rag = RagService(embedder=get_embedding_provider(), chunk_repo=self.chunk_repo)
        hits = await rag.retrieve(scenario_id=scenario.id, query=user_text, k=5)

        context = "\n\n".join(h.chunk.content for h in hits) or "(нет источников)"
        prompt = (
            f"Вопрос пользователя: {user_text}\n\n"
            f"Контекст из базы знаний:\n{context}\n\n"
            "Ответь кратко, опираясь только на контекст. Не придумывай."
        )
        llm_resp = self.llm.generate(
            LLMRequest(prompt=prompt, task="info", max_tokens=512)
        )

        answer = with_disclaimer(llm_resp.text)
        citations = [
                        Citation(
                            url=h.chunk.source_url,
                            title=h.chunk.source_title,
                            type=h.chunk.source_type,
                            chunk_index=h.chunk.chunk_index,
                        )
                        for h in hits
                    ] or None

        await self._save_turn(
            dialog.id,
            turn_index=assistant_index,
            role="assistant",
            content=answer,
            citations=[c.model_dump() for c in citations] if citations else None,
        )
        dialog.state = DialogState.INFO_READY.value

        return MessageOut(
            session_id=dialog.id,
            state=dialog.state,
            content=answer,
            citations=citations,
            disclaimer=DISCLAIMER,
        )

    # ---------- trainer branch ----------

    async def _handle_trainer(
            self, dialog: DialogSession, user_text: str, assistant_index: int
    ) -> MessageOut:
        scenario = await self.session.get(Scenario, dialog.scenario_id)
        assert scenario is not None
        cases = load_cases(scenario.slug)
        if not cases:
            raise DialogError(400, "no_cases", "no cases for scenario")

        # Пересортировываем кейсы, чтобы следующий вопрос был из слабой зоны
        cases = await reorder_cases_by_weak_zones(
            cases,
            profile_id=dialog.user_profile_id,
            scenario_slug=scenario.slug,
            session=self.session,
        )

        answered_cases = await self._count_user_turns(dialog.id)
        case = cases[min(answered_cases - 1, len(cases) - 1)]

        evaluation = evaluate_answer(user_text, case)
        feedback_text = self._render_feedback(evaluation)

        # Запоминаем слабую зону, если ответ не идеальный
        if evaluation.verdict != "good" and dialog.user_profile_id is not None:
            await record_weak_zone(
                self.session,
                profile_id=dialog.user_profile_id,
                code=case.weak_zone_code,
                scenario_slug=scenario.slug,
            )

        if answered_cases >= len(cases):
            dialog.state = DialogState.FINISHED.value
            content = with_disclaimer(
                f"{feedback_text}\n\nВсе кейсы пройдены. Спасибо за работу!"
            )
            next_case_question = None
        else:
            next_case = cases[answered_cases]
            dialog.state = DialogState.AWAITING_ANSWER.value
            content = with_disclaimer(
                f"{feedback_text}\n\nСледующий кейс: {next_case.question}"
            )
            next_case_question = next_case.question

        await self._save_turn(
            dialog.id,
            turn_index=assistant_index,
            role="assistant",
            content=content,
            evaluation={
                "verdict": evaluation.verdict,
                "mistakes": evaluation.mistakes,
                "score": evaluation.score,
                "case_id": case.id,
            },
        )

        return MessageOut(
            session_id=dialog.id,
            state=dialog.state,
            content=content,
            evaluation=EvaluationOut(
                verdict=evaluation.verdict,
                mistakes=evaluation.mistakes,
                improvements=evaluation.improvements,
                exemplar=evaluation.exemplar,
                score=evaluation.score,
            ),
            disclaimer=DISCLAIMER,
        )

    @staticmethod
    def _render_feedback(evaluation: Evaluation) -> str:
        if evaluation.verdict == "good":
            head = "Это верно."
        elif evaluation.verdict == "incomplete":
            head = "Ответ пока неполный."
        else:
            head = "Вот что можно улучшить."
        parts = [head, evaluation.improvements]
        if evaluation.exemplar:
            parts.append(f"Удачный пример: {evaluation.exemplar}")
        return "\n\n".join(parts)

    # ---------- helpers ----------

    async def _require_scenario(self, slug: str) -> Scenario:
        scenario = await self.scenario_repo.get_by_slug(slug)
        if scenario is None or not scenario.is_active:
            raise DialogError(404, "scenario_not_found", f"scenario '{slug}' not found")
        return scenario

    async def _require_session(self, session_id: uuid.UUID) -> DialogSession:
        dialog = await self.session.get(DialogSession, session_id)
        if dialog is None:
            raise DialogError(404, "session_not_found", "session not found")
        return dialog

    async def _ensure_profile(self, anonymous_id: str | None) -> UserProfile | None:
        if not anonymous_id:
            return None
        result = await self.session.execute(
            select(UserProfile).where(UserProfile.anonymous_id == anonymous_id)
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            profile = UserProfile(anonymous_id=anonymous_id)
            self.session.add(profile)
            await self.session.flush()
        return profile

    async def _next_turn_index(self, session_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(Turn.turn_index)
            .where(Turn.session_id == session_id)
            .order_by(Turn.turn_index.desc())
            .limit(1)
        )
        last = result.scalar_one_or_none()
        return 0 if last is None else last + 1

    async def _count_user_turns(self, session_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(Turn).where(Turn.session_id == session_id, Turn.role == "user")
        )
        return len(list(result.scalars().all()))

    async def _save_turn(
            self,
            session_id: uuid.UUID,
            *,
            turn_index: int,
            role: str,
            content: str,
            evaluation: dict | None = None,
            citations: list[dict] | None = None,
    ) -> None:
        self.session.add(
            Turn(
                session_id=session_id,
                turn_index=turn_index,
                role=role,
                content=content,
                evaluation=evaluation,
                citations=citations,
            )
        )
        await self.session.flush()