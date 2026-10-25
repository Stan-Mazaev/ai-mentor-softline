from __future__ import annotations

DISCLAIMER = (
    "Рекомендации носят информационный характер и не заменяют "
    "официальные требования вузов и работодателей."
)


def with_disclaimer(text: str) -> str:
    if not text:
        return f"_{DISCLAIMER}_"
    return f"{text}\n\n_{DISCLAIMER}_"