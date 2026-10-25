import uuid

import pytest

from app.export.pdf import PDFExportError, export_session_pdf
from app.models.dialog_session import DialogSession
from app.models.scenario import Scenario
from app.models.turn import Turn


async def test_pdf_export_smoke(db_session):
    scenario = Scenario(slug="s1", title="Тест", description="", is_active=True)
    db_session.add(scenario)
    await db_session.commit()

    dialog = DialogSession(scenario_id=scenario.id, mode="info", state="info_ready")
    db_session.add(dialog)
    await db_session.commit()

    db_session.add(Turn(session_id=dialog.id, turn_index=0, role="assistant",
                        content="Здравствуйте!"))
    await db_session.commit()

    try:
        pdf_bytes = await export_session_pdf(dialog.id, db_session)
    except PDFExportError:
        pytest.skip("no cyrillic font on this host")

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500


async def test_pdf_export_missing_session(db_session):
    with pytest.raises(PDFExportError):
        await export_session_pdf(uuid.uuid4(), db_session)