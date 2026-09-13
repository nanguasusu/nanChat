from typing import Literal

from pydantic import BaseModel, Field


class MessageReference(BaseModel):
    parent_id: str
    document_id: str
    content: str
    filename: str
    source: str
    page_start: int | None
    page_end: int | None
    score: float
    score_type: Literal["rrf", "reranker"] = "rrf"
    hit_count: int
    matched_child_ids: list[str]


class ThreadResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    reasoning_content: str = ""
    thinking_duration_ms: int = 0
    references: list[MessageReference] = Field(default_factory=list)
