from typing import TypedDict

from app.agentic_rag.schemas import RetrievalPlan, TaskResult
from app.rag.schemas import RetrievedParent


class AgenticRagState(TypedDict):
    question: str
    history: list[dict[str, str]]
    initial_context: list[RetrievedParent]
    plan: RetrievalPlan | None
    scope_results: list[TaskResult]
    task_results: list[TaskResult]
    final_answer: str
    references: list[RetrievedParent]
