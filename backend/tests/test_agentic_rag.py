import asyncio
import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.agentic_rag.executor import execute_task, execute_tasks, merge_references
from app.agentic_rag.graph import run_agentic_rag
from app.agentic_rag.schemas import (
    AgenticRagResult,
    PlanTask,
    RetrievalPlan,
    SeedQueryResult,
    TaskAnswer,
)
from app.rag.schemas import RetrievedParent
from app.schemas.chat import ChatRequest
from app.schemas.thread import MessageResponse, ThreadResponse
from app.services.chat_service import stream_chat_response


def parent(parent_id: str, score: float = 0.8) -> RetrievedParent:
    return RetrievedParent(
        parent_id=parent_id,
        document_id="doc",
        content=f"evidence-{parent_id}",
        filename="法典.pdf",
        source="knowledge/法典.pdf",
        page_start=1,
        page_end=1,
        score=score,
        hit_count=1,
        matched_child_ids=[f"child-{parent_id}"],
    )


async def no_stage(stage: str, status: str, **payload: object) -> None:
    return None


class AgenticGraphTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_plan_skips_task_retrieval(self) -> None:
        empty_plan = RetrievalPlan(
            scope_only=False,
            resolved_query="法定继承顺序",
            tasks=[],
        )
        with (
            patch("app.agentic_rag.graph.retrieve", AsyncMock(return_value=[parent("p1")])),
            patch("app.agentic_rag.graph.create_plan", AsyncMock(return_value=empty_plan)),
            patch("app.agentic_rag.graph.execute_tasks", AsyncMock()) as execute,
            patch(
                "app.agentic_rag.graph.synthesize_answer",
                AsyncMock(return_value="第一顺序后第二顺序。"),
            ),
        ):
            result = await run_agentic_rag("法定继承顺序是什么？", [], object(), "model")

        self.assertEqual(result.answer, "第一顺序后第二顺序。")
        self.assertEqual([item.parent_id for item in result.references], ["p1"])
        execute.assert_not_awaited()

    async def test_multi_part_plan_executes_distinct_tasks(self) -> None:
        plan = RetrievalPlan(
            scope_only=False,
            resolved_query="比较两种继承",
            tasks=[
                PlanTask(id="t1", question="法定继承适用条件是什么？", query="法定继承 适用条件"),
                PlanTask(id="t2", question="遗嘱继承优先顺序是什么？", query="遗嘱继承 优先顺序"),
            ],
        )
        with (
            patch("app.agentic_rag.graph.retrieve", AsyncMock(return_value=[])),
            patch("app.agentic_rag.graph.create_plan", AsyncMock(return_value=plan)),
            patch("app.agentic_rag.graph.execute_tasks", AsyncMock(return_value=[])) as execute,
            patch("app.agentic_rag.graph.synthesize_answer", AsyncMock(return_value="比较结果")),
        ):
            await run_agentic_rag("比较法定继承和遗嘱继承", [], object(), "model")

        tasks = execute.await_args.args[2]
        self.assertEqual({task.query for task in tasks}, {"法定继承 适用条件", "遗嘱继承 优先顺序"})

    async def test_scope_discovery_replans_once(self) -> None:
        scope_plan = RetrievalPlan(
            scope_only=True,
            resolved_query="所有情形",
            tasks=[PlanTask(id="s1", question="有哪些类别？", query="相关类别")],
        )
        answer_plan = RetrievalPlan(
            scope_only=False,
            resolved_query="所有情形",
            tasks=[PlanTask(id="t1", question="逐项说明类别", query="类别 条件")],
        )
        with (
            patch("app.agentic_rag.graph.retrieve", AsyncMock(return_value=[])),
            patch(
                "app.agentic_rag.graph.create_plan",
                AsyncMock(side_effect=[scope_plan, answer_plan]),
            ) as planner,
            patch("app.agentic_rag.graph.execute_tasks", AsyncMock(side_effect=[[], []])) as execute,
            patch("app.agentic_rag.graph.synthesize_answer", AsyncMock(return_value="完整结果")),
        ):
            await run_agentic_rag("列出所有情形", [], object(), "model")

        self.assertEqual(planner.await_count, 2)
        self.assertEqual(execute.await_count, 2)
        self.assertFalse(planner.await_args.args[-1])

    async def test_scope_replan_cannot_start_second_scope_round(self) -> None:
        scope_plan = RetrievalPlan(
            scope_only=True,
            resolved_query="范围",
            tasks=[PlanTask(id="s1", question="范围？", query="范围")],
        )
        invalid_second_scope = RetrievalPlan(
            scope_only=True,
            resolved_query="范围",
            tasks=[PlanTask(id="t1", question="答案？", query="答案")],
        )
        with (
            patch("app.agentic_rag.graph.retrieve", AsyncMock(return_value=[])),
            patch(
                "app.agentic_rag.graph.create_plan",
                AsyncMock(side_effect=[scope_plan, invalid_second_scope]),
            ),
            patch("app.agentic_rag.graph.execute_tasks", AsyncMock(side_effect=[[], []])) as execute,
            patch("app.agentic_rag.graph.synthesize_answer", AsyncMock(return_value="结果")),
        ):
            await run_agentic_rag("范围", [], object(), "model")

        self.assertEqual(execute.await_count, 2)


class TaskExecutionTests(unittest.IsolatedAsyncioTestCase):
    async def test_partial_task_retries_exactly_once(self) -> None:
        task = PlanTask(id="t1", question="条件和顺序？", query="条件")
        with (
            patch("app.agentic_rag.executor.retrieve", AsyncMock(side_effect=[[parent("p1")], [parent("p2")]])) as retrieval,
            patch(
                "app.agentic_rag.executor._answer_task",
                AsyncMock(
                    side_effect=[
                        TaskAnswer(completeness="partial", answer="已有条件", missing="优先顺序"),
                        TaskAnswer(completeness="complete", answer="已有条件及顺序"),
                    ]
                ),
            ),
            patch(
                "app.agentic_rag.executor._seed_query",
                AsyncMock(return_value=SeedQueryResult(query="继承 优先顺序", stop=False, reason="补缺")),
            ) as seed,
        ):
            result = await execute_task(object(), "model", task, 2, no_stage)

        self.assertEqual(retrieval.await_count, 2)
        seed.assert_awaited_once()
        self.assertEqual(result.attempts, 2)
        self.assertEqual(result.answer, "已有条件及顺序")
        self.assertEqual([item.parent_id for item in result.references], ["p1", "p2"])

    async def test_complete_task_does_not_generate_seed(self) -> None:
        task = PlanTask(id="t1", question="条件？", query="条件")
        with (
            patch("app.agentic_rag.executor.retrieve", AsyncMock(return_value=[parent("p1")])),
            patch(
                "app.agentic_rag.executor._answer_task",
                AsyncMock(return_value=TaskAnswer(completeness="complete", answer="完整")),
            ),
            patch("app.agentic_rag.executor._seed_query", AsyncMock()) as seed,
        ):
            result = await execute_task(object(), "model", task, 2, no_stage)

        seed.assert_not_awaited()
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.attempts, 1)

    async def test_one_task_failure_does_not_cancel_others(self) -> None:
        tasks = [
            PlanTask(id="bad", question="失败", query="bad"),
            PlanTask(id="good", question="成功", query="good"),
        ]

        async def retrieval(query: str):
            if query == "bad":
                raise RuntimeError("retrieval failed")
            return [parent("p1")]

        with (
            patch("app.agentic_rag.executor.retrieve", retrieval),
            patch(
                "app.agentic_rag.executor._answer_task",
                AsyncMock(return_value=TaskAnswer(completeness="complete", answer="完成")),
            ),
        ):
            results = await execute_tasks(object(), "model", tasks, 2, 3, no_stage)

        self.assertEqual([result.status for result in results], ["error", "complete"])

    async def test_reference_merge_deduplicates_and_keeps_best_score(self) -> None:
        merged = merge_references([parent("p1", 0.7), parent("p2"), parent("p1", 0.9)])
        self.assertEqual([item.parent_id for item in merged], ["p1", "p2"])
        self.assertEqual(merged[0].score, 0.9)


class RegressionContractTests(unittest.TestCase):
    def test_standard_rag_remains_default(self) -> None:
        request = ChatRequest(message="问题", rag_enabled=True)
        self.assertEqual(request.rag_mode, "standard")


class StandardRagServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_standard_rag_keeps_existing_retrieve_then_stream_path(self) -> None:
        class EmptyStream:
            def __aiter__(self):
                return self

            async def __anext__(self):
                raise StopAsyncIteration

            async def close(self) -> None:
                return None

        completion_create = AsyncMock(return_value=EmptyStream())
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=completion_create)
            ),
            close=AsyncMock(),
        )
        thread = ThreadResponse(
            id="thread-1",
            title="问题",
            created_at="2026-09-13T00:00:00+00:00",
            updated_at="2026-09-13T00:00:00+00:00",
        )
        history = [MessageResponse(id="user-1", role="user", content="问题")]
        http_request = SimpleNamespace(is_disconnected=AsyncMock(return_value=False))

        with (
            patch("app.services.chat_service.get_longcat_settings", return_value=object()),
            patch("app.services.chat_service.get_longcat_client", return_value=client),
            patch("app.services.chat_service.create_thread_with_message", return_value=thread),
            patch("app.services.chat_service.get_thread", return_value=thread),
            patch("app.services.chat_service.list_messages", return_value=history),
            patch("app.services.chat_service.add_message"),
            patch("app.services.chat_service.retrieve", AsyncMock(return_value=[parent("p1")])) as retrieval,
            patch("app.services.chat_service.run_agentic_rag", AsyncMock()) as agentic,
        ):
            chunks = [
                chunk
                async for chunk in stream_chat_response(
                    ChatRequest(message="问题", rag_enabled=True),
                    http_request,
                )
            ]

        events = [json.loads(chunk.removeprefix("data: ")) for chunk in chunks]
        retrieval.assert_awaited_once_with("问题")
        agentic.assert_not_awaited()
        self.assertEqual(events[0]["type"], "start")
        self.assertEqual(events[-1]["type"], "done")
        self.assertEqual(events[-1]["references"][0]["parent_id"], "p1")

    async def test_agentic_mode_emits_stage_and_reuses_done_contract(self) -> None:
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=AsyncMock())
            ),
            close=AsyncMock(),
        )
        thread = ThreadResponse(
            id="thread-1",
            title="问题",
            created_at="2026-09-13T00:00:00+00:00",
            updated_at="2026-09-13T00:00:00+00:00",
        )
        history = [MessageResponse(id="user-1", role="user", content="问题")]
        http_request = SimpleNamespace(is_disconnected=AsyncMock(return_value=False))

        async def agentic_run(question, history, client, model, callback, **kwargs):
            await callback("initial_retrieval", "start")
            await callback("planning", "done", task_count=0)
            return AgenticRagResult(answer="合成答案", references=[parent("p1")])

        with (
            patch("app.services.chat_service.get_longcat_settings", return_value=object()),
            patch("app.services.chat_service.get_longcat_client", return_value=client),
            patch("app.services.chat_service.create_thread_with_message", return_value=thread),
            patch("app.services.chat_service.get_thread", return_value=thread),
            patch("app.services.chat_service.list_messages", return_value=history),
            patch("app.services.chat_service.add_message"),
            patch("app.services.chat_service.run_agentic_rag", agentic_run),
            patch("app.services.chat_service.rewrite_query", AsyncMock()) as rewrite,
        ):
            chunks = [
                chunk
                async for chunk in stream_chat_response(
                    ChatRequest(
                        message="问题",
                        rag_enabled=True,
                        rag_mode="agentic",
                        query_rewrite_enabled=True,
                    ),
                    http_request,
                )
            ]

        events = [json.loads(chunk.removeprefix("data: ")) for chunk in chunks]
        self.assertIn("agentic_stage", [event["type"] for event in events])
        self.assertEqual(next(event for event in events if event["type"] == "delta")["content"], "合成答案")
        self.assertEqual(events[-1]["type"], "done")
        self.assertEqual(events[-1]["references"][0]["parent_id"], "p1")
        client.chat.completions.create.assert_not_awaited()
        rewrite.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
