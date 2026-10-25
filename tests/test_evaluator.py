from app.dialog.cases import Case
from app.dialog.evaluator import evaluate_answer


def _case() -> Case:
    return Case(
        id="t1",
        question="Что в резюме кроме образования?",
        expected_hints=("pet-проекты", "стажировки", "навыки"),
        typical_mistakes=("ничего не умею",),
        exemplar="Укажу pet-проекты, стажировки и навыки.",
    )


def test_good_answer():
    ev = evaluate_answer(
        "Укажу pet-проекты и стажировки, плюс конкретные навыки.",
        _case(),
    )
    assert ev.verdict == "good"


def test_typical_mistake_flagged():
    ev = evaluate_answer("Я ничего не умею, возьмите меня так", _case())
    assert ev.verdict == "needs_improvement"
    assert "ничего не умею" in ev.mistakes


def test_incomplete_short_answer():
    ev = evaluate_answer("не знаю", _case())
    assert ev.verdict in {"incomplete", "needs_improvement"}
    assert ev.score <= 0.3