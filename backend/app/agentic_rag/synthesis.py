"""根据初始证据和任务结果生成 Agentic RAG 的最终回答。"""

from collections.abc import Awaitable, Callable

from openai import AsyncOpenAI

from app.agentic_rag.prompts import format_evidence, format_task_results
from app.agentic_rag.schemas import RetrievalPlan, TaskResult
from app.rag.schemas import RetrievedParent
from app.services.model_params import get_thinking_parameters

TokenCallback = Callable[[str], Awaitable[None]]


def _delta_extra(delta: object) -> dict[str, object]:
    """读取 OpenAI 增量对象中的扩展字段。"""
    extra = getattr(delta, "model_extra", None)
    return extra if isinstance(extra, dict) else {}


async def synthesize_answer(
    client: AsyncOpenAI,
    model: str,
    question: str,
    initial_context: list[RetrievedParent],
    plan: RetrievalPlan,
    task_results: list[TaskResult],
    on_delta: TokenCallback | None = None,
    on_reasoning: TokenCallback | None = None,
) -> str:
    """流式合成最终答案，并分别转发正文和思考增量。"""
    prompt = f"""你是企业知识库助手。请生成正常、自然的最终回答。

用户原始问题：{question}
解析后的问题：{plan.resolved_query}
回答侧重点：{plan.synthesis_instruction or '直接回答用户问题'}

初始检索资料：
{format_evidence(initial_context)}

任务结果：
{format_task_results(task_results)}

只能使用上述资料与任务答案。综合回答原始问题，也检查初始资料中任务未覆盖的信息；证据不足时明确说明，不得编造事实或引文。不要提到规划器、任务、RAG、Seed Query 等内部术语。"""
    stream = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=4096,
        extra_body=get_thinking_parameters(model),
        stream=True,
    )
    parts: list[str] = []
    try:
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            reasoning = _delta_extra(delta).get("reasoning_content", "")
            if reasoning and on_reasoning:
                await on_reasoning(str(reasoning))
            content = delta.content
            if not content:
                continue
            parts.append(content)
            if on_delta:
                await on_delta(content)
    finally:
        await stream.close()
    return "".join(parts)
