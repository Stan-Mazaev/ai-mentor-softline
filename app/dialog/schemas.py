from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    scenario_slug: str = Field(min_length=1, max_length=64)
    mode: Literal["info", "trainer"]
    anonymous_id: str | None = Field(default=None, max_length=64)


class Citation(BaseModel):
    url: str
    title: str
    type: str
    chunk_index: int


class SessionOut(BaseModel):
    id: UUID
    scenario_slug: str
    mode: str
    state: str
    initial_message: str


class MessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class EvaluationOut(BaseModel):
    verdict: Literal["good", "needs_improvement", "incomplete"]
    mistakes: list[str]
    improvements: str
    exemplar: str
    score: float


class MessageOut(BaseModel):
    session_id: UUID
    state: str
    role: Literal["assistant"] = "assistant"
    content: str
    evaluation: EvaluationOut | None = None
    citations: list[Citation] | None = None
    disclaimer: str | None = None