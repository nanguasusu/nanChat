"""Agentic RAG 规划、任务执行和最终结果的数据模型。"""

from typing import Literal

from pydantic import BaseModel, Field

from app.rag.schemas import RetrievedParent


class PlanTask(BaseModel):
    """一个待检索任务，同时保存面向模型的问题和检索 query。"""

    id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    query: str = Field(min_length=1)


class RetrievalPlan(BaseModel):
    """规划器生成的任务列表及最终回答指引。"""

    scope_only: bool
    scope_resolution: str = ""
    resolved_query: str = Field(min_length=1)
    tasks: list[PlanTask] = Field(default_factory=list)
    synthesis_instruction: str = ""


class TaskAnswer(BaseModel):
    """任务回答器对证据完整性的判断和答案。"""

    completeness: Literal["complete", "partial", "none"]
    answer: str
    missing: str = ""


class SeedQueryResult(BaseModel):
    """缺失证据重试查询及是否停止重试。"""

    query: str | None = None
    stop: bool
    reason: str


class TaskResult(BaseModel):
    """一次任务执行的答案、状态、尝试次数和引用。"""

    task_id: str
    question: str
    answer: str
    status: Literal["complete", "partial", "no_data", "error"]
    attempts: int
    references: list[RetrievedParent] = Field(default_factory=list)


class AgenticRagResult(BaseModel):
    """Agentic RAG 对外返回的最终答案和引用。"""

    answer: str
    references: list[RetrievedParent]
