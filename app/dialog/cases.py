from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

KB_ROOT = Path(__file__).resolve().parent.parent.parent / "knowledge_base"


@dataclass(frozen=True)
class Case:
    id: str
    question: str
    expected_hints: tuple[str, ...]
    typical_mistakes: tuple[str, ...]
    exemplar: str
    weak_zone_code: str = ""


def load_cases(scenario_slug: str, kb_root: Path | None = None) -> list[Case]:
    root = kb_root or KB_ROOT
    file = root / scenario_slug / "cases.json"
    if not file.exists():
        return []
    data = json.loads(file.read_text(encoding="utf-8"))
    return [
        Case(
            id=c["id"],
            question=c["question"],
            expected_hints=tuple(c.get("expected_hints", [])),
            typical_mistakes=tuple(c.get("typical_mistakes", [])),
            exemplar=c.get("exemplar", ""),
            weak_zone_code=c.get("weak_zone_code", c["id"]),
        )
        for c in data.get("cases", [])
    ]