from typing import Literal

from pydantic import BaseModel, Field

from app.rag.schemas import RetrievedParent


class PlanTask(BaseModel):
    id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    query: str = Field(min_length=1)


class RetrievalPlan(BaseModel):
    scope_only: bool
    scope_resolution: str = ""
    resolved_query: str = Field(min_length=1)
    tasks: list[PlanTask] = Field(default_factory=list)
    synthesis_instruction: str = ""


class TaskAnswer(BaseModel):
    completeness: Literal["complete", "partial", "none"]
    answer: str
    missing: str = ""


class SeedQueryResult(BaseModel):
    query: str | None = None
    stop: bool
    reason: str


class TaskResult(BaseModel):
    task_id: str
    question: str
    answer: str
    status: Literal["complete", "partial", "no_data", "error"]
    attempts: int
    references: list[RetrievedParent] = Field(default_factory=list)


class AgenticRagResult(BaseModel):
    answer: str
    references: list[RetrievedParent]
