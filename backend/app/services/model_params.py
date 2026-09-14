"""把前端思考档位转换为各模型接受的请求参数。"""

FORCED_THINKING_MODELS = {"glm-5.3", "glm-5.3-flash"}

FORCED_THINKING_EFFORTS = {
    "off": "low",
    "low": "low",
    "medium": "high",
    "high": "high",
    "xhigh": "max",
}

ANSWER_TOKEN_BUDGET = 4096
THINKING_TOKEN_BUDGETS = {
    "off": 1024,
    "low": 1024,
    "medium": 2048,
    "high": 4096,
    "xhigh": 8192,
}


def get_completion_max_tokens(thinking_level: str) -> int:
    """Cap thinking and the visible answer separately; APIs often count both in max_tokens."""
    return THINKING_TOKEN_BUDGETS[thinking_level] + ANSWER_TOKEN_BUDGET


def get_thinking_parameters(
    model: str,
    thinking_level: str | None = None,
) -> dict[str, object]:
    """生成 thinking 参数；强制思考模型使用兼容的 reasoning_effort。"""
    if model in FORCED_THINKING_MODELS:
        level = thinking_level or "low"
        return {
            "thinking": {"type": "enabled"},
            "reasoning_effort": FORCED_THINKING_EFFORTS[level],
        }

    return {
        "thinking": {
            "type": "enabled" if thinking_level and thinking_level != "off" else "disabled"
        }
    }
