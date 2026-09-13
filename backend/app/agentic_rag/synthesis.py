import logging

from openai import AsyncOpenAI

from app.agentic_rag.prompts import format_evidence, format_task_results
from app.agentic_rag.schemas import RetrievalPlan, TaskResult
from app.rag.schemas import RetrievedParent
from app.services.model_params import get_thinking_parameters

logger = logging.getLogger(__name__)


async def synthesize_answer(
    client: AsyncOpenAI,
    model: str,
    question: str,
    initial_context: list[RetrievedParent],
    plan: RetrievalPlan,
    task_results: list[TaskResult],
) -> str:
    prompt = f"""你是企业知识库助手。请生成正常、自然的最终回答。

用户原始问题：{question}
解析后的问题：{plan.resolved_query}
回答侧重点：{plan.synthesis_instruction or '直接回答用户问题'}

初始检索资料：
{format_evidence(initial_context)}

任务结果：
{format_task_results(task_results)}

只能使用上述资料与任务答案。综合回答原始问题，也检查初始资料中任务未覆盖的信息；证据不足时明确说明，不得编造事实或引文。不要提到规划器、任务、RAG、Seed Query 等内部术语。"""
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=4096,
        extra_body=get_thinking_parameters(model),
    )
    answer = response.choices[0].message.content or ""
    logger.info(
        "Agentic synthesis: tasks_complete=%d",
        sum(result.status == "complete" for result in task_results),
    )
    return answer
