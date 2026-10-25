from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from app.dialog.cases import Case


@dataclass
class Evaluation:
    verdict: Literal["good", "needs_improvement", "incomplete"]
    mistakes: list[str] = field(default_factory=list)
    improvements: str = ""
    exemplar: str = ""
    score: float = 0.0


_STOPWORDS = {
    "и", "в", "на", "не", "что", "как", "это", "я", "мы", "вы", "по",
    "с", "к", "из", "у", "о", "об", "но", "или", "а", "же", "бы",
}


def _tokenize(text: str) -> list[str]:
    words = re.findall(r"\w+", text.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 2]


def evaluate_answer(answer: str, case: Case) -> Evaluation:
    text = answer.strip()
    if len(text) < 10:
        return Evaluation(
            verdict="incomplete",
            mistakes=["ответ слишком короткий"],
            improvements="Дайте более развёрнутый ответ: что вы сделаете и почему.",
            exemplar=case.exemplar,
            score=0.0,
        )

    lowered = text.lower()
    found_mistakes = [
        m for m in case.typical_mistakes if m.lower() in lowered
    ]

    answer_tokens = set(_tokenize(text))
    hint_hits = 0
    for hint in case.expected_hints:
        hint_tokens = set(_tokenize(hint))
        if hint_tokens and hint_tokens <= answer_tokens:
            hint_hits += 1

    total_hints = max(1, len(case.expected_hints))
    coverage = hint_hits / total_hints
    score = max(0.0, min(1.0, coverage - 0.2 * len(found_mistakes)))

    if found_mistakes and len(found_mistakes) >= max(1, len(case.typical_mistakes) // 2):
        verdict: Literal["good", "needs_improvement", "incomplete"] = "needs_improvement"
    elif coverage >= 0.5 and not found_mistakes:
        verdict = "good"
    elif coverage < 0.2:
        verdict = "needs_improvement"
    else:
        verdict = "needs_improvement"

    if verdict == "good":
        improvements = (
            "Ответ сильный. Чтобы усилить — добавьте измеримый результат "
            "или короткий пример из своего опыта."
        )
    else:
        hints_list = "; ".join(case.expected_hints[:3])
        improvements = (
            "Добавьте конкретики: что именно вы сделаете, с какими сроками "
            f"и на какой результат ориентируетесь. Опорные точки: {hints_list}."
        )
        if found_mistakes:
            improvements += f" Проблемные формулировки: {', '.join(found_mistakes)}."

    return Evaluation(
        verdict=verdict,
        mistakes=found_mistakes,
        improvements=improvements,
        exemplar=case.exemplar,
        score=round(score, 3),
    )