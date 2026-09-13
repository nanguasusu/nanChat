FORCED_THINKING_MODELS = {"glm-5.3", "glm-5.3-flash"}

FORCED_THINKING_EFFORTS = {
    "off": "low",
    "low": "low",
    "medium": "high",
    "high": "high",
    "xhigh": "max",
}


def get_thinking_parameters(
    model: str,
    thinking_level: str | None = None,
) -> dict[str, object]:
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
