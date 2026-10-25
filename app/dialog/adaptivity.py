from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dialog.cases import Case
from app.models.weak_zone import WeakZone


async def reorder_cases_by_weak_zones(
    cases: list[Case],
    *,
    profile_id: uuid.UUID | None,
    scenario_slug: str,
    session: AsyncSession,
) -> list[Case]:
    """Ставит первыми кейсы, соответствующие слабым зонам пользователя.

    Стабильная сортировка: кейсы с большим hit_count идут первыми, остальные —
    в исходном порядке из cases.json.
    """
    if not cases or profile_id is None:
        return cases

    result = await session.execute(
        select(WeakZone).where(
            WeakZone.profile_id == profile_id,
            WeakZone.scenario_slug == scenario_slug,
        )
    )
    weights = {wz.code: wz.hit_count for wz in result.scalars().all()}
    if not weights:
        return cases

    indexed = list(enumerate(cases))
    indexed.sort(key=lambda ic: (-weights.get(ic[1].weak_zone_code, 0), ic[0]))
    return [c for _, c in indexed]


async def record_weak_zone(
    session: AsyncSession,
    *,
    profile_id: uuid.UUID,
    code: str,
    scenario_slug: str,
) -> None:
    if not code:
        return
    result = await session.execute(
        select(WeakZone).where(
            WeakZone.profile_id == profile_id,
            WeakZone.code == code,
            WeakZone.scenario_slug == scenario_slug,
        )
    )
    wz = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if wz is None:
        session.add(
            WeakZone(
                profile_id=profile_id,
                code=code,
                scenario_slug=scenario_slug,
                hit_count=1,
                last_seen_at=now,
            )
        )
    else:
        wz.hit_count += 1
        wz.last_seen_at = now
    await session.flush()