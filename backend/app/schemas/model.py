"""模型列表接口使用的数据模型。"""

from typing import Literal

from pydantic import BaseModel

ThinkingLevel = Literal["off", "low", "medium", "high", "xhigh"]


class ModelResponse(BaseModel):
    """描述前端可选择的模型和思考参数。"""

    id: str
    label: str
    context_window_tokens: int
    thinking_levels: list[ThinkingLevel]
