from __future__ import annotations

import uuid
from pathlib import Path

from fpdf import FPDF
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dialog_session import DialogSession
from app.models.scenario import Scenario
from app.models.turn import Turn
from app.models.user_profile import UserProfile
from app.models.weak_zone import WeakZone

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\DejaVuSans.ttf",
]

DISCLAIMER_TEXT = (
    "Рекомендации носят информационный характер и не заменяют "
    "официальные требования вузов и работодателей."
)


class PDFExportError(RuntimeError):
    pass


def _find_font() -> str | None:
    for p in _FONT_CANDIDATES:
        if Path(p).exists():
            return p
    return None


async def export_session_pdf(
    session_id: uuid.UUID, session: AsyncSession
) -> bytes:
    dialog = await session.get(DialogSession, session_id)
    if dialog is None:
        raise PDFExportError("session not found")

    scenario = await session.get(Scenario, dialog.scenario_id)
    if scenario is None:
        raise PDFExportError("scenario not found")

    turns_result = await session.execute(
        select(Turn).where(Turn.session_id == session_id).order_by(Turn.turn_index)
    )
    turns = list(turns_result.scalars().all())

    weak_zones: list[WeakZone] = []
    if dialog.user_profile_id:
        wz_result = await session.execute(
            select(WeakZone)
            .where(
                WeakZone.profile_id == dialog.user_profile_id,
                WeakZone.scenario_slug == scenario.slug,
            )
            .order_by(WeakZone.hit_count.desc())
        )
        weak_zones = list(wz_result.scalars().all())

    font_path = _find_font()
    if font_path is None:
        raise PDFExportError(
            "no cyrillic-capable font found (install DejaVuSans or Arial)"
        )

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.add_font("main", "", font_path)
    pdf.set_font("main", size=16)
    pdf.cell(0, 10, text="AI-тренажёр: отчёт по сессии", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("main", size=10)
    pdf.cell(0, 6, text=f"Сценарий: {scenario.title} ({scenario.slug})", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, text=f"Режим: {dialog.mode}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, text=f"Сессия: {dialog.id}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    if weak_zones:
        pdf.set_font("main", size=13)
        pdf.cell(0, 8, text="Слабые зоны", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("main", size=10)
        for wz in weak_zones:
            pdf.multi_cell(
                0, 6,
                text=f"- {wz.code}: {wz.hit_count} раз",
                new_x="LMARGIN", new_y="NEXT",
            )
        pdf.ln(3)

    pdf.set_font("main", size=13)
    pdf.cell(0, 8, text="Диалог", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    role_labels = {"user": "Вы", "assistant": "Наставник", "system": "Система"}
    for turn in turns:
        label = role_labels.get(turn.role, turn.role)
        pdf.set_font("main", size=11)
        pdf.multi_cell(0, 6, text=f"[{label}]", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("main", size=10)
        pdf.multi_cell(0, 5, text=turn.content, new_x="LMARGIN", new_y="NEXT")

        if turn.evaluation:
            ev = turn.evaluation
            mistakes = ", ".join(ev.get("mistakes") or []) or "—"
            pdf.set_font("main", size=9)
            pdf.multi_cell(
                0, 5,
                text=(
                    f"  Вердикт: {ev.get('verdict')} (score {ev.get('score')}). "
                    f"Ошибки: {mistakes}"
                ),
                new_x="LMARGIN", new_y="NEXT",
            )

        if turn.citations:
            urls = ", ".join(c.get("url", "") for c in turn.citations[:3])
            pdf.set_font("main", size=9)
            pdf.multi_cell(
                0, 5, text=f"  Источники: {urls}",
                new_x="LMARGIN", new_y="NEXT",
            )
        pdf.ln(2)

    pdf.ln(4)
    pdf.set_font("main", size=9)
    pdf.multi_cell(0, 5, text=DISCLAIMER_TEXT, new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())