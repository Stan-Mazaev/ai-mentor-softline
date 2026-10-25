import uuid
from typing import Any

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPkMixin


class Turn(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "turns"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dialog_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)          # user|assistant|system
    content: Mapped[str] = mapped_column(Text, nullable=False)             # уже PII-маскированный
    evaluation: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    citations: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)