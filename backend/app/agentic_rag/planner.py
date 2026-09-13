import json
import logging
import re

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.agentic_rag.prompts import format_evidence, format_task_results
from app.agentic_rag.schemas import RetrievalPlan, TaskResult
from app.rag.schemas import RetrievedParent
from app.services.model_params import get_thinking_parameters

logger = logging.getLogger(__name__)


def _json_object(content: str) -> dict[str, object]:
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", content, re.DOTALL)
    return json.loads(fenced.group(1) if fenced else content)


async def create_plan(
    client: AsyncOpenAI,
    model: str,
    question: str,
    history: list[dict[str, str]],
    initial_context: list[RetrievedParent],
    scope_results: list[TaskResult],
    max_tasks: int,
    max_scope_tasks: int,
    allow_scope: bool,
) -> RetrievalPlan:
    recent_history = history[-4:]
    prompt = f"""你是企业知识库检索规划器。只输出严格 JSON，不要输出解释或 Markdown。

原始问题：{question}
近期对话：{json.dumps(recent_history, ensure_ascii=False)}

初始检索样本：
{format_evidence(initial_context)}

范围探索结果：
{format_task_results(scope_results)}

输出结构：
{{"scope_only": false, "scope_resolution": "", "resolved_query": "...", "tasks": [{{"id": "t1", "question": "...", "query": "..."}}], "synthesis_instruction": "..."}}

规则：初始检索只是语料库样本，没出现不代表不存在。若样本已完整回答，tasks 为空。只为缺失信息创建任务，不要过度拆分，优先 1-3 个，最多 {max_tasks} 个。question 是任务模型要回答的问题，query 是发给检索器的简短自然查询，二者用途不同。禁止生成同义改写式重复任务。
若问题要求完整、穷尽、全面覆盖，且样本不能确定语料范围，可设置 scope_only=true，以最多 {max_scope_tasks} 个任务探索相关类别或条文；探索任务不直接回答最终问题。当前允许范围探索：{str(allow_scope).lower()}。若不允许，scope_only 必须为 false，并依据探索结果产生最终回答任务。"""
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1600,
            extra_body=get_thinking_parameters(model),
        )
        plan = RetrievalPlan.model_validate(
            _json_object(response.choices[0].message.content or "")
        )
        task_limit = max_scope_tasks if plan.scope_only else max_tasks
        plan = plan.model_copy(update={"tasks": plan.tasks[:task_limit]})
        if not allow_scope and plan.scope_only:
            plan = plan.model_copy(update={"scope_only": False})
        return plan
    except (ValidationError, json.JSONDecodeError, IndexError, TypeError) as error:
        logger.warning("Agentic planner failed; using initial-context fallback: %s", error)
        return RetrievalPlan(
            scope_only=False,
            resolved_query=question,
            tasks=[],
            synthesis_instruction="请直接根据初始检索资料回答。",
        )
