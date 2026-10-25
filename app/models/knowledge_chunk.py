import uuid
from typing import Any

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPkMixin


class KnowledgeChunk(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_chunks"

    scenario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scenarios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_title: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)  # official|reviews|forum|academic

    chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Пока храним как JSON list[float]. На Postgres+pgvector переедет в vector(384).
    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)

    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)