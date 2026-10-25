from __future__ import annotations

import re
from dataclasses import dataclass, field

EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")

# +7 999 123-45-67 / +7 (999) 123-45-67 / 89991234567 — скобки и разделители опциональны
PHONE_RE = re.compile(
    r"(?:\+7|\b8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b"
)

NAME_RE = re.compile(r"\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?\b")

# школе/школа/школы, гимназии, лицея, СОШ, МБОУ, МАОУ
SCHOOL_RE = re.compile(
    r"\b(?:школ\w*|гимнази\w*|лице\w*|СОШ|МБОУ|МАОУ)\s*№?\s*\d{1,4}\b",
    re.IGNORECASE,
)

# «10 класс», «10-А класс», «10 А классе» — буква перед «класс» только если за ней пробел
CLASS_RE = re.compile(
    r"\b\d{1,2}\s*[-–]?\s*(?:[А-Яа-я]\s+)?класс\w*",
    re.IGNORECASE,
)


@dataclass
class MaskResult:
    text: str
    found: dict[str, int] = field(default_factory=dict)

    @property
    def masked_anything(self) -> bool:
        return any(v > 0 for v in self.found.values())


def mask_pii(text: str) -> MaskResult:
    if not text:
        return MaskResult(text="")

    counts: dict[str, int] = {}

    def _sub(pattern: re.Pattern[str], placeholder: str, key: str) -> None:
        nonlocal text

        def repl(_m: re.Match[str]) -> str:
            counts[key] = counts.get(key, 0) + 1
            return placeholder

        text = pattern.sub(repl, text)

    _sub(EMAIL_RE, "<EMAIL>", "email")
    _sub(PHONE_RE, "<PHONE>", "phone")
    _sub(SCHOOL_RE, "<SCHOOL>", "school")
    _sub(CLASS_RE, "<CLASS>", "class")
    _sub(NAME_RE, "<NAME>", "name")

    return MaskResult(text=text, found={k: v for k, v in counts.items() if v > 0})