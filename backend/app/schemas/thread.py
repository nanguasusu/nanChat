"""会话、消息及知识库引用的 API 数据模型。"""

from typing import Literal

from pydantic import BaseModel, Field


class MessageReference(BaseModel):
    """一条消息引用的 Parent 文档片段及其检索信息。"""

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
    """会话列表和会话创建接口返回的数据。"""

    id: str
    title: str
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    """消息内容、思考耗时以及可选知识库引用。"""

    id: str
    role: Literal["user", "assistant"]
    content: str
    reasoning_content: str = ""
    thinking_duration_ms: int = 0
    references: list[MessageReference] = Field(default_factory=list)
