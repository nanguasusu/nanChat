from typing import Literal

from pydantic import BaseModel, Field

ThinkingLevel = Literal["off", "low", "medium", "high", "xhigh"]
RagMode = Literal["standard", "agentic"]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    thread_id: str | None = None
    model: str | None = None
    thinking_level: ThinkingLevel = "medium"
    rag_enabled: bool = False
    rag_mode: RagMode = "standard"
    query_rewrite_enabled: bool = False
