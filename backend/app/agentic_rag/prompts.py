"""控制 Agentic RAG 提示词中的证据数量和文本长度。"""

from app.agentic_rag.schemas import TaskResult
from app.rag.schemas import RetrievedParent

MAX_PROMPT_PARENTS = 12
MAX_PROMPT_CHARS = 24_000


def select_context(parents: list[RetrievedParent]) -> list[RetrievedParent]:
    """按分数去重并截断证据，控制单次提示词的规模。"""
    best_by_id: dict[str, RetrievedParent] = {}
    for parent in parents:
        current = best_by_id.get(parent.parent_id)
        if current is None or parent.score > current.score:
            best_by_id[parent.parent_id] = parent

    selected: list[RetrievedParent] = []
    used_chars = 0
    for parent in sorted(best_by_id.values(), key=lambda item: item.score, reverse=True):
        if len(selected) >= MAX_PROMPT_PARENTS:
            break
        remaining = MAX_PROMPT_CHARS - used_chars
        if remaining <= 0:
            break
        if len(parent.content) > remaining:
            parent = parent.model_copy(update={"content": parent.content[:remaining]})
        selected.append(parent)
        used_chars += len(parent.content)
    return selected


def format_evidence(parents: list[RetrievedParent]) -> str:
    """把 Parent 证据格式化为带文件名和页码的提示词文本。"""
    if not parents:
        return "（没有检索到相关资料）"
    blocks = []
    for index, parent in enumerate(select_context(parents), start=1):
        page = (
            "无页码"
            if parent.page_start is None
            else f"第 {parent.page_start} 页"
            if parent.page_start == parent.page_end
            else f"第 {parent.page_start}-{parent.page_end} 页"
        )
        blocks.append(f"资料 {index}｜{parent.filename}｜{page}\n{parent.content}")
    return "\n\n".join(blocks)


def format_task_results(results: list[TaskResult]) -> str:
    """把任务状态和答案格式化为最终合成可读的文本。"""
    if not results:
        return "（没有任务结果）"
    return "\n\n".join(
        f"任务：{result.question}\n状态：{result.status}\n答案：{result.answer}"
        for result in results
        if result.status != "error" or result.answer
    ) or "（没有可用的任务结果）"
