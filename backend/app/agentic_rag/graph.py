import logging
from collections.abc import Awaitable, Callable

from langgraph.graph import END, START, StateGraph
from openai import AsyncOpenAI

from app.agentic_rag.executor import execute_tasks, merge_references
from app.agentic_rag.planner import create_plan
from app.agentic_rag.schemas import AgenticRagResult
from app.agentic_rag.state import AgenticRagState
from app.agentic_rag.synthesis import synthesize_answer
from app.core.config import get_agentic_rag_settings
from app.rag.retrieval_service import retrieve

logger = logging.getLogger(__name__)
StageCallback = Callable[..., Awaitable[None]]


async def _ignore_stage(stage: str, status: str, **payload: object) -> None:
    pass


async def run_agentic_rag(
    question: str,
    history: list[dict[str, str]],
    client: AsyncOpenAI,
    model: str,
    stage_callback: StageCallback = _ignore_stage,
) -> AgenticRagResult:
    settings = get_agentic_rag_settings()

    async def initial_retrieval(state: AgenticRagState) -> dict[str, object]:
        await stage_callback("initial_retrieval", "start")
        parents = await retrieve(state["question"])
        logger.info("Agentic initial retrieval: parents=%d", len(parents))
        await stage_callback(
            "initial_retrieval", "done", parent_count=len(parents)
        )
        return {"initial_context": parents}

    async def plan(state: AgenticRagState) -> dict[str, object]:
        await stage_callback("planning", "start")
        retrieval_plan = await create_plan(
            client,
            model,
            state["question"],
            state["history"],
            state["initial_context"],
            [],
            settings.max_plan_tasks,
            settings.max_scope_tasks,
            True,
        )
        logger.info(
            "Agentic planner: scope_only=%s tasks=%d",
            retrieval_plan.scope_only,
            len(retrieval_plan.tasks),
        )
        await stage_callback(
            "planning", "done", task_count=len(retrieval_plan.tasks)
        )
        return {"plan": retrieval_plan}

    async def execute_scope(state: AgenticRagState) -> dict[str, object]:
        results = await execute_tasks(
            client,
            model,
            state["plan"].tasks,
            settings.task_max_retrievals,
            settings.max_concurrency,
            stage_callback,
        )
        return {"scope_results": results}

    async def replan(state: AgenticRagState) -> dict[str, object]:
        await stage_callback("planning", "start")
        retrieval_plan = await create_plan(
            client,
            model,
            state["question"],
            state["history"],
            state["initial_context"],
            state["scope_results"],
            settings.max_plan_tasks,
            settings.max_scope_tasks,
            False,
        )
        await stage_callback(
            "planning", "done", task_count=len(retrieval_plan.tasks)
        )
        return {"plan": retrieval_plan}

    async def execute(state: AgenticRagState) -> dict[str, object]:
        results = await execute_tasks(
            client,
            model,
            state["plan"].tasks,
            settings.task_max_retrievals,
            settings.max_concurrency,
            stage_callback,
        )
        return {"task_results": results}

    async def synthesize(state: AgenticRagState) -> dict[str, object]:
        await stage_callback("synthesis", "start")
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
            client,
            model,
            state["question"],
            state["initial_context"],
            state["plan"],
            state["task_results"],
        )
        logger.info("Agentic synthesis: references=%d", len(references))
        await stage_callback("synthesis", "done")
        return {"final_answer": answer, "references": references}

    def route_plan(state: AgenticRagState) -> str:
        if not state["plan"].tasks:
            return "synthesize"
        return "execute_scope" if state["plan"].scope_only else "execute"

    def route_replan(state: AgenticRagState) -> str:
        return "execute" if state["plan"].tasks else "synthesize"

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
    builder.add_edge("synthesize", END)  # Extension point: future verification.
    graph = builder.compile()

    final_state = await graph.ainvoke(
        AgenticRagState(
            question=question,
            history=history,
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
