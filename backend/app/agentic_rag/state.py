"""LangGraph 在 Agentic RAG 各节点之间传递的状态定义。"""

from typing import Any, TypedDict

from app.agentic_rag.schemas import RetrievalPlan, TaskResult
from app.rag.schemas import RetrievedParent


class AgenticRagState(TypedDict):
    """一次 Agentic 运行的输入、过程结果和最终输出。"""

    question: str
    history: list[dict[str, str]]
    runtime: Any
    initial_context: list[RetrievedParent]
    plan: RetrievalPlan | None
    scope_results: list[TaskResult]
    task_results: list[TaskResult]
    final_answer: str
    references: list[RetrievedParent]
