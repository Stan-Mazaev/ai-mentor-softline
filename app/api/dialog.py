from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.dialog.schemas import MessageIn, MessageOut, SessionCreate, SessionOut
from app.dialog.service import DialogError, DialogService
from app.dialog.states import DialogMode
from app.export.pdf import PDFExportError, export_session_pdf
from app.llm import LLMGateway, get_llm_gateway

router = APIRouter(prefix="/dialog", tags=["dialog"])


def _service(
        session: AsyncSession = Depends(get_session),
        llm: LLMGateway = Depends(get_llm_gateway),
) -> DialogService:
    return DialogService(session=session, llm=llm)


def _to_http(exc: DialogError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message})


@router.post("/sessions", response_model=SessionOut)
async def create_session(
        payload: SessionCreate, service: DialogService = Depends(_service)
) -> SessionOut:
    try:
        return await service.create_session(
            scenario_slug=payload.scenario_slug,
            mode=DialogMode(payload.mode),
            anonymous_id=payload.anonymous_id,
        )
    except DialogError as exc:
        raise _to_http(exc) from exc


@router.post("/sessions/{session_id}/messages", response_model=MessageOut)
async def post_message(
        session_id: uuid.UUID,
        payload: MessageIn,
        service: DialogService = Depends(_service),
) -> MessageOut:
    try:
        return await service.post_message(session_id=session_id, content=payload.content)
    except DialogError as exc:
        raise _to_http(exc) from exc


@router.get("/sessions/{session_id}/export.pdf")
async def export_pdf(
        session_id: uuid.UUID,
        session: AsyncSession = Depends(get_session),
) -> Response:
    try:
        pdf_bytes = await export_session_pdf(session_id, session)
    except PDFExportError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="session-{session_id}.pdf"'
        },
    )