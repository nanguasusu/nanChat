import asyncio
import json
import logging

from openai import AsyncOpenAI, OpenAIError
from pydantic import ValidationError

from app.agentic_rag.planner import _json_object
from app.agentic_rag.prompts import format_evidence, select_context
from app.agentic_rag.schemas import PlanTask, SeedQueryResult, TaskAnswer, TaskResult
from app.rag.retrieval_service import retrieve
from app.rag.schemas import RetrievedParent
from app.services.model_params import get_thinking_parameters

logger = logging.getLogger(__name__)


def merge_references(parents: list[RetrievedParent]) -> list[RetrievedParent]:
    best_by_id: dict[str, RetrievedParent] = {}
    order: list[str] = []
    for parent in parents:
        if parent.parent_id not in best_by_id:
            order.append(parent.parent_id)
            best_by_id[parent.parent_id] = parent
        elif parent.score > best_by_id[parent.parent_id].score:
            best_by_id[parent.parent_id] = parent
    return [best_by_id[parent_id] for parent_id in order]


async def _answer_task(
    client: AsyncOpenAI,
    model: str,
    task: PlanTask,
    parents: list[RetrievedParent],
    previous_answer: str = "",
) -> TaskAnswer:
    prompt = f"""你是受控的知识库任务回答器。只输出严格 JSON：
{{"completeness":"complete|partial|none","answer":"...","missing":"..."}}

任务问题：{task.question}
上一轮部分答案：{previous_answer or '（无）'}
检索资料：
{format_evidence(parents)}

只能使用给定资料，只回答任务问题，不添加外部事实。资料完全支持答案时为 complete；有相关证据但仍缺少具体信息时为 partial，并在 missing 明确缺什么；没有有用证据时为 none。重试时把上一轮已支持内容与新资料合并为一个答案。法律内容应保持原意，不得捏造引文。"""
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=1400,
        extra_body=get_thinking_parameters(model),
    )
    return TaskAnswer.model_validate(
        _json_object(response.choices[0].message.content or "")
    )


async def _seed_query(
    client: AsyncOpenAI,
    model: str,
    task: PlanTask,
    previous_query: str,
    answer: TaskAnswer,
) -> SeedQueryResult:
    prompt = f"""你是缺失证据查询生成器。只输出严格 JSON：
{{"query":"...或null","stop":false,"reason":"..."}}

任务：{task.question}
上一查询：{previous_query}
部分答案：{answer.answer}
缺失信息：{answer.missing}

只针对缺失信息生成一次新查询，使用不同术语或检索角度，不要重复搜索已有证据，不要只做表面同义改写。若再次检索不太可能有帮助，令 stop=true 且 query=null。"""
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=500,
        extra_body=get_thinking_parameters(model),
    )
    return SeedQueryResult.model_validate(
        _json_object(response.choices[0].message.content or "")
    )


async def execute_task(
    client: AsyncOpenAI,
    model: str,
    task: PlanTask,
    max_retrievals: int,
    stage_callback,
) -> TaskResult:
    references: list[RetrievedParent] = []
    query = task.query
    previous_answer = ""
    attempts = 0
    try:
        await stage_callback("task", "start", task_id=task.id, label=task.question)
        while attempts < max_retrievals:
            attempts += 1
            new_parents = await retrieve(query)
            references = merge_references([*references, *new_parents])
            answer = await _answer_task(
                client,
                model,
                task,
                select_context(references if attempts > 1 else new_parents),
                previous_answer,
            )
            logger.info(
                "Agentic task %s: attempt=%d parents=%d completeness=%s",
                task.id,
                attempts,
                len(new_parents),
                answer.completeness,
            )
            previous_answer = answer.answer
            if answer.completeness != "partial" or attempts >= max_retrievals:
                status = "no_data" if answer.completeness == "none" else answer.completeness
                await stage_callback(
                    "task",
                    "done",
                    task_id=task.id,
                    attempts=attempts,
                    result_status=status,
                )
                return TaskResult(
                    task_id=task.id,
                    question=task.question,
                    answer=answer.answer,
                    status=status,
                    attempts=attempts,
                    references=references,
                )
            try:
                seed = await _seed_query(client, model, task, query, answer)
            except (ValidationError, json.JSONDecodeError, IndexError, TypeError):
                break
            if seed.stop or not seed.query:
                break
            query = seed.query
            logger.info("Agentic task %s: retry query=%r", task.id, query)
            await stage_callback(
                "task", "retry", task_id=task.id, attempts=attempts + 1
            )
    except asyncio.CancelledError:
        raise
    except OpenAIError:
        raise
    except Exception as error:
        logger.warning("Agentic task %s failed: %s", task.id, error)
        await stage_callback(
            "task",
            "done",
            task_id=task.id,
            attempts=attempts,
            result_status="error",
        )
        return TaskResult(
            task_id=task.id,
            question=task.question,
            answer="",
            status="error",
            attempts=attempts,
            references=references,
        )

    await stage_callback(
        "task",
        "done",
        task_id=task.id,
        attempts=attempts,
        result_status="partial",
    )
    return TaskResult(
        task_id=task.id,
        question=task.question,
        answer=previous_answer,
        status="partial",
        attempts=attempts,
        references=references,
    )


async def execute_tasks(
    client: AsyncOpenAI,
    model: str,
    tasks: list[PlanTask],
    max_retrievals: int,
    max_concurrency: int,
    stage_callback,
) -> list[TaskResult]:
    semaphore = asyncio.Semaphore(max_concurrency)

    async def run(task: PlanTask) -> TaskResult:
        async with semaphore:
            return await execute_task(
                client, model, task, max_retrievals, stage_callback
            )

    return list(await asyncio.gather(*(run(task) for task in tasks)))
