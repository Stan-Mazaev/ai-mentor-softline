from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scenario import Scenario


class ScenarioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_slug(self, slug: str) -> Scenario | None:
        result = await self.session.execute(select(Scenario).where(Scenario.slug == slug))
        return result.scalar_one_or_none()

    async def list_active(self) -> list[Scenario]:
        result = await self.session.execute(
            select(Scenario).where(Scenario.is_active.is_(True)).order_by(Scenario.slug)
        )
        return list(result.scalars().all())

    async def create(self, *, slug: str, title: str, description: str = "") -> Scenario:
        scenario = Scenario(slug=slug, title=title, description=description)
        self.session.add(scenario)
        await self.session.commit()
        await self.session.refresh(scenario)
        return scenario