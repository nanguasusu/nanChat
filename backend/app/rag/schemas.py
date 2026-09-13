from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.config import MAX_RAG_TOP_K


class RetrievedParent(BaseModel):
    parent_id: str
    document_id: str
    content: str
    filename: str
    source: str
    page_start: int | None
    page_end: int | None
    score: float
    score_type: Literal["rrf", "reranker"] = "reranker"
    hit_count: int
    matched_child_ids: list[str]


class RagSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    k: int | None = Field(default=None, ge=1, le=MAX_RAG_TOP_K)

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query must not be blank")
        return value


class RagSearchResponse(BaseModel):
    query: str
    results: list[RetrievedParent]
