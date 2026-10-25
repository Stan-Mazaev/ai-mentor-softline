from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.scenario import ScenarioRepository
from app.schemas.rag import ScenarioOut

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("", response_model=list[ScenarioOut])
async def list_scenarios(session: AsyncSession = Depends(get_session)) -> list[ScenarioOut]:
    repo = ScenarioRepository(session)
    scenarios = await repo.list_active()
    return [ScenarioOut.model_validate(s) for s in scenarios]