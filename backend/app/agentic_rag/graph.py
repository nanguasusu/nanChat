"""定义 Agentic RAG 的检索、规划、执行和合成状态图。"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from langgraph.graph import END, START, StateGraph
from openai import AsyncOpenAI

from app.agentic_rag.executor import execute_tasks, merge_references
from app.agentic_rag.planner import create_plan
from app.agentic_rag.schemas import AgenticRagResult
from app.agentic_rag.state import AgenticRagState
from app.agentic_rag.synthesis import synthesize_answer
from app.core.config import AgenticRAGSettings, get_agentic_rag_settings
from app.rag.retrieval_service import retrieve
from app.rag.schemas import RetrievedParent

logger = logging.getLogger(__name__)
StageCallback = Callable[..., Awaitable[None]]
TokenCallback = Callable[[str], Awaitable[None]]


@dataclass
class AgenticRuntime:
    """状态图节点共享的模型客户端、运行限制和事件回调。"""

    client: AsyncOpenAI
    model: str
    settings: AgenticRAGSettings
    stage_callback: StageCallback
    on_answer_delta: TokenCallback | None = None
    on_reasoning_delta: TokenCallback | None = None


async def _ignore_stage(stage: str, status: str, **payload: object) -> None:
    """默认忽略阶段事件，供非流式调用复用同一套图逻辑。"""
    pass


def _runtime(state: AgenticRagState) -> AgenticRuntime:
    """从状态中取出节点运行时依赖。"""
    return state["runtime"]


async def initial_retrieval(state: AgenticRagState) -> dict[str, object]:
    """先做一次宽检索，为规划器提供语料样本。"""
    runtime = _runtime(state)
    await runtime.stage_callback("initial_retrieval", "start")
    parents = await retrieve(state["question"])
    logger.info("Agentic initial retrieval: parents=%d", len(parents))
    await runtime.stage_callback(
        "initial_retrieval", "done", parent_count=len(parents)
    )
    return {"initial_context": parents}


async def plan(state: AgenticRagState) -> dict[str, object]:
    """根据问题、历史和初始资料决定任务拆分或范围探索。"""
    runtime = _runtime(state)
    await runtime.stage_callback("planning", "start")
    retrieval_plan = await create_plan(
        runtime.client,
        runtime.model,
        state["question"],
        state["history"],
        state["initial_context"],
        [],
        runtime.settings.max_plan_tasks,
        runtime.settings.max_scope_tasks,
        True,
    )
    logger.info(
        "Agentic planner: scope_only=%s tasks=%d",
        retrieval_plan.scope_only,
        len(retrieval_plan.tasks),
    )
    await runtime.stage_callback(
        "planning", "done", task_count=len(retrieval_plan.tasks)
    )
    return {"plan": retrieval_plan}


def _shared_evidence(state: AgenticRagState) -> list[RetrievedParent]:
    """合并初始资料与范围探索结果，作为后续任务的共享证据。"""
    return merge_references(
        [
            *state["initial_context"],
            *(
                parent
                for result in state["scope_results"]
                for parent in result.references
            ),
        ]
    )


async def execute_scope(state: AgenticRagState) -> dict[str, object]:
    """执行范围探索任务，为下一轮最终规划补充类别信息。"""
    runtime = _runtime(state)
    results = await execute_tasks(
        runtime.client,
        runtime.model,
        state["plan"].tasks,
        runtime.settings.task_max_retrievals,
        runtime.settings.max_concurrency,
        runtime.stage_callback,
        shared_evidence=_shared_evidence(state),
    )
    return {"scope_results": results}


async def replan(state: AgenticRagState) -> dict[str, object]:
    """结合范围探索结果生成最终回答任务；本轮禁止再次范围探索。"""
    runtime = _runtime(state)
    await runtime.stage_callback("planning", "start")
    retrieval_plan = await create_plan(
        runtime.client,
        runtime.model,
        state["question"],
        state["history"],
        state["initial_context"],
        state["scope_results"],
        runtime.settings.max_plan_tasks,
        runtime.settings.max_scope_tasks,
        False,
    )
    await runtime.stage_callback(
        "planning", "done", task_count=len(retrieval_plan.tasks)
    )
    return {"plan": retrieval_plan}


async def execute(state: AgenticRagState) -> dict[str, object]:
    """并发执行最终规划中的检索回答任务。"""
    runtime = _runtime(state)
    results = await execute_tasks(
        runtime.client,
        runtime.model,
        state["plan"].tasks,
        runtime.settings.task_max_retrievals,
        runtime.settings.max_concurrency,
        runtime.stage_callback,
        shared_evidence=_shared_evidence(state),
    )
    return {"task_results": results}


async def synthesize(state: AgenticRagState) -> dict[str, object]:
    """综合初始资料和任务答案，并收集最终去重引用。"""
    runtime = _runtime(state)
    await runtime.stage_callback("synthesis", "start")
    references = merge_references(
        [
            *state["initial_context"],
            *(
                parent
                for result in [*state["scope_results"], *state["task_results"]]
                for parent in result.references
            ),
        ]
    )
    answer = await synthesize_answer(
        runtime.client,
        runtime.model,
        state["question"],
        state["initial_context"],
        state["plan"],
        state["task_results"],
        on_delta=runtime.on_answer_delta,
        on_reasoning=runtime.on_reasoning_delta,
    )
    logger.info("Agentic synthesis: references=%d", len(references))
    await runtime.stage_callback("synthesis", "done")
    return {"final_answer": answer, "references": references}


def route_plan(state: AgenticRagState) -> str:
    """空计划直接合成；否则进入范围探索或最终任务执行。"""
    if not state["plan"].tasks:
        return "synthesize"
    return "execute_scope" if state["plan"].scope_only else "execute"


def route_replan(state: AgenticRagState) -> str:
    """范围探索后的计划有任务才执行，否则直接合成。"""
    return "execute" if state["plan"].tasks else "synthesize"


def _build_graph():
    """组装并编译 Agentic RAG 状态图。"""
    builder = StateGraph(AgenticRagState)
    builder.add_node("initial_retrieval", initial_retrieval)
    builder.add_node("plan", plan)
    builder.add_node("execute_scope", execute_scope)
    builder.add_node("replan", replan)
    builder.add_node("execute", execute)
    builder.add_node("synthesize", synthesize)
    builder.add_edge(START, "initial_retrieval")
    builder.add_edge("initial_retrieval", "plan")
    builder.add_conditional_edges("plan", route_plan)
    builder.add_edge("execute_scope", "replan")
    builder.add_conditional_edges("replan", route_replan)
    builder.add_edge("execute", "synthesize")
    builder.add_edge("synthesize", END)
    return builder.compile()


_graph = _build_graph()


async def run_agentic_rag(
    question: str,
    history: list[dict[str, str]],
    client: AsyncOpenAI,
    model: str,
    stage_callback: StageCallback = _ignore_stage,
    on_answer_delta: TokenCallback | None = None,
    on_reasoning_delta: TokenCallback | None = None,
) -> AgenticRagResult:
    """运行一次 Agentic RAG，并返回最终答案及合并后的引用。"""
    runtime = AgenticRuntime(
        client=client,
        model=model,
        settings=get_agentic_rag_settings(),
        stage_callback=stage_callback,
        on_answer_delta=on_answer_delta,
        on_reasoning_delta=on_reasoning_delta,
    )
    final_state = await _graph.ainvoke(
        AgenticRagState(
            question=question,
            history=history,
            runtime=runtime,
            initial_context=[],
            plan=None,
            scope_results=[],
            task_results=[],
            final_answer="",
            references=[],
        )
    )
    return AgenticRagResult(
        answer=final_state["final_answer"],
        references=final_state["references"],
    )
