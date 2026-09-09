from typing import Literal

from pydantic import BaseModel


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
