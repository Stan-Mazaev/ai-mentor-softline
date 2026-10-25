from __future__ import annotations

from app.llm.base import LLMRequest, LLMResponse


class StubLLMProvider:
    """Детерминированный провайдер для локальной разработки и тестов.

    Не зовёт внешние API, отдаёт предсказуемые ответы.
    Заменяется на Yandex/GigaChat в get_llm_provider() без изменений в коде выше.
    """

    name = "stub"
    model = "stub-1"

    def generate(self, request: LLMRequest) -> LLMResponse:
        if request.task == "info":
            text = (
                "По вашему вопросу я нашёл материалы в базе знаний — "
                "они перечислены в источниках к этому ответу. "
                "Если нужна конкретика, уточните: сроки, документы, критерии отбора."
            )
        elif request.task == "feedback":
            text = (
                "Спасибо за ответ. В нём есть сильные стороны, но не хватает конкретики. "
                "Сравните с примером удачного ответа ниже и попробуйте переформулировать."
            )
        else:
            head = request.prompt.strip().split("\n", 1)[0][:200]
            text = f"Stub-ответ: {head}"

        tokens_in = max(1, len(request.prompt.split()))
        tokens_out = max(1, len(text.split()))
        return LLMResponse(
            text=text,
            model=self.model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            metadata={"provider": self.name, "task": request.task},
        )