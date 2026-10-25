from fastapi import APIRouter

from app.api import dialog, health, rag, scenarios

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(scenarios.router)
api_router.include_router(rag.router)
api_router.include_router(dialog.router)