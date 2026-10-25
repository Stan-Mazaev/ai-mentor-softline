from app.models.scenario import Scenario
from app.models.user_profile import UserProfile
from app.models.weak_zone import WeakZone
from app.repositories.scenario import ScenarioRepository


async def test_create_scenario(db_session):
    repo = ScenarioRepository(db_session)
    s = await repo.create(slug="university_choice", title="Выбор вуза")

    found = await repo.get_by_slug("university_choice")
    assert found is not None
    assert found.id == s.id
    assert found.title == "Выбор вуза"


async def test_scenario_list_active(db_session):
    repo = ScenarioRepository(db_session)
    await repo.create(slug="a", title="A")
    await repo.create(slug="b", title="B")
    active = await repo.list_active()
    assert {s.slug for s in active} == {"a", "b"}


async def test_user_profile_and_weak_zone(db_session):
    profile = UserProfile(anonymous_id="anon-123")
    db_session.add(profile)
    await db_session.commit()

    wz = WeakZone(profile_id=profile.id, code="no_portfolio", scenario_slug="first_job", hit_count=1)
    db_session.add(wz)
    await db_session.commit()

    assert wz.id is not None
    assert wz.hit_count == 1