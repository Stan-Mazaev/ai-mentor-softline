from pydantic import BaseModel, Field


class ScenarioOut(BaseModel):
    slug: str
    title: str
    description: str

    model_config = {"from_attributes": True}


class Citation(BaseModel):
    url: str
    title: str
    type: str
    chunk_index: int


class RagHit(BaseModel):
    content: str
    score: float
    citation: Citation


class RagSearchRequest(BaseModel):
    scenario_slug: str = Field(min_length=1, max_length=64)
    query: str = Field(min_length=1, max_length=2000)
    k: int = Field(default=5, ge=1, le=20)


class RagSearchResponse(BaseModel):
    hits: list[RagHit]