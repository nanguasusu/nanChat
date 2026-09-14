"""知识库检索接口和检索结果的数据模型。"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.config import MAX_RAG_TOP_K


class RetrievedParent(BaseModel):
    """供回答模型和前端引用展示的 Parent 检索结果。"""

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
    """独立检索接口的 query 和可选返回数量。"""

    query: str = Field(min_length=1)
    k: int | None = Field(default=None, ge=1, le=MAX_RAG_TOP_K)

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        """拒绝只包含空白字符的检索问题。"""
        if not value.strip():
            raise ValueError("query must not be blank")
        return value


class RagSearchResponse(BaseModel):
    """独立检索接口的原始 query 和结果列表。"""

    query: str
    results: list[RetrievedParent]
