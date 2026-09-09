from typing import Literal

from pydantic import BaseModel

ThinkingLevel = Literal["off", "low", "medium", "high", "xhigh"]


class ModelResponse(BaseModel):
    id: str
    label: str
    context_window_tokens: int
    thinking_levels: list[ThinkingLevel]
