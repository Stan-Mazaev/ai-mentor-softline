from app.dialog.adaptivity import record_weak_zone, reorder_cases_by_weak_zones
from app.dialog.cases import Case
from app.models.user_profile import UserProfile


def _cases() -> list[Case]:
    return [
        Case(id="a", question="A", expected_hints=(), typical_mistakes=(),
             exemplar="", weak_zone_code="zone_a"),
        Case(id="b", question="B", expected_hints=(), typical_mistakes=(),
             exemplar="", weak_zone_code="zone_b"),
        Case(id="c", question="C", expected_hints=(), typical_mistakes=(),
             exemplar="", weak_zone_code="zone_c"),
    ]


async def test_reorder_without_profile_keeps_order(db_session):
    ordered = await reorder_cases_by_weak_zones(
        _cases(), profile_id=None, scenario_slug="x", session=db_session,
    )
    assert [c.id for c in ordered] == ["a", "b", "c"]


async def test_reorder_by_hit_count(db_session):
    profile = UserProfile(anonymous_id="anon-1")
    db_session.add(profile)
    await db_session.commit()

    for _ in range(3):
        await record_weak_zone(db_session, profile_id=profile.id,
                               code="zone_b", scenario_slug="x")
    await db_session.commit()

    ordered = await reorder_cases_by_weak_zones(
        _cases(), profile_id=profile.id, scenario_slug="x", session=db_session,
    )
    assert [c.id for c in ordered] == ["b", "a", "c"]


async def test_record_weak_zone_increments(db_session):
    profile = UserProfile(anonymous_id="anon-2")
    db_session.add(profile)
    await db_session.commit()

    await record_weak_zone(db_session, profile_id=profile.id,
                           code="zone_a", scenario_slug="x")
    await record_weak_zone(db_session, profile_id=profile.id,
                           code="zone_a", scenario_slug="x")
    await db_session.commit()

    from sqlalchemy import select
    from app.models.weak_zone import WeakZone
    result = await db_session.execute(
        select(WeakZone).where(WeakZone.profile_id == profile.id)
    )
    wz = result.scalar_one()
    assert wz.hit_count == 2