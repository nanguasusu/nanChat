"""封装会话和消息的 SQLite 持久化操作。"""

import json
from datetime import datetime, timezone
from uuid import uuid4

from app.core.database import get_connection
from app.schemas.thread import MessageReference, MessageResponse, ThreadResponse


class ThreadNotFoundError(LookupError):
    """请求的会话不存在时抛出。"""


def _now() -> str:
    """生成统一的 UTC ISO 时间戳。"""
    return datetime.now(timezone.utc).isoformat()


def _thread_from_row(row) -> ThreadResponse:
    """把 SQLite 行转换为会话响应模型。"""
    return ThreadResponse(
        id=row["id"],
        title=row["title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _message_from_row(row) -> MessageResponse:
    """把 SQLite 行及 JSON 引用转换为消息响应模型。"""
    return MessageResponse(
        id=row["id"],
        role=row["role"],
        content=row["content"],
        reasoning_content=row["reasoning_content"],
        thinking_duration_ms=row["thinking_duration_ms"],
        references=[
            MessageReference.model_validate(reference)
            for reference in json.loads(row["references_json"])
        ],
    )


async def list_threads() -> list[ThreadResponse]:
    """按最近更新时间倒序读取所有会话。"""
    async with get_connection() as connection:
        cursor = await connection.execute(
            "SELECT id, title, created_at, updated_at FROM threads ORDER BY updated_at DESC"
        )
        rows = await cursor.fetchall()
    return [_thread_from_row(row) for row in rows]


async def create_thread(title: str = "New chat") -> ThreadResponse:
    """创建一个尚未包含消息的新会话。"""
    thread_id = str(uuid4())
    timestamp = _now()
    normalized_title = " ".join(title.split())[:80] or "New chat"

    async with get_connection() as connection:
        await connection.execute(
            "INSERT INTO threads (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (thread_id, normalized_title, timestamp, timestamp),
        )

    return await get_thread(thread_id)


async def create_thread_with_message(title: str, content: str) -> ThreadResponse:
    """在同一事务中创建会话和首条用户消息。"""
    thread_id = str(uuid4())
    created_at = _now()
    message_id = str(uuid4())
    message_created_at = _now()
    normalized_title = " ".join(title.split())[:80] or "New chat"

    async with get_connection() as connection:
        await connection.execute(
            "INSERT INTO threads (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (thread_id, normalized_title, created_at, message_created_at),
        )
        await connection.execute(
            """
            INSERT INTO messages (
                id, thread_id, role, content, reasoning_content, thinking_duration_ms, created_at
            )
            VALUES (?, ?, 'user', ?, '', 0, ?)
            """,
            (message_id, thread_id, content, message_created_at),
        )
        cursor = await connection.execute(
            "SELECT id, title, created_at, updated_at FROM threads WHERE id = ?",
            (thread_id,),
        )
        row = await cursor.fetchone()

    return _thread_from_row(row)


async def get_thread(thread_id: str) -> ThreadResponse:
    """读取会话，不存在时抛出明确的业务异常。"""
    async with get_connection() as connection:
        cursor = await connection.execute(
            "SELECT id, title, created_at, updated_at FROM threads WHERE id = ?",
            (thread_id,),
        )
        row = await cursor.fetchone()

    if row is None:
        raise ThreadNotFoundError(thread_id)
    return _thread_from_row(row)


async def delete_thread(thread_id: str) -> None:
    """删除会话；消息由数据库外键级联删除。"""
    async with get_connection() as connection:
        cursor = await connection.execute("DELETE FROM threads WHERE id = ?", (thread_id,))

    if cursor.rowcount == 0:
        raise ThreadNotFoundError(thread_id)


async def update_thread_title(thread_id: str, title: str) -> ThreadResponse:
    """规范化并更新会话标题，然后返回最新会话。"""
    normalized_title = " ".join(title.split())[:80] or "New chat"
    async with get_connection() as connection:
        await connection.execute(
            "UPDATE threads SET title = ?, updated_at = ? WHERE id = ?",
            (normalized_title, _now(), thread_id),
        )
    return await get_thread(thread_id)


async def add_message(
    thread_id: str,
    role: str,
    content: str,
    reasoning_content: str = "",
    thinking_duration_ms: int = 0,
    references: list[MessageReference] | None = None,
    message_id: str | None = None,
) -> MessageResponse:
    """保存消息及其引用，并同步刷新会话更新时间。"""
    message_id = message_id or str(uuid4())
    timestamp = _now()
    serialized_references = json.dumps(
        [reference.model_dump(mode="json") for reference in references or []],
        ensure_ascii=False,
    )
    async with get_connection() as connection:
        await connection.execute(
            """
            INSERT INTO messages (
                id, thread_id, role, content, reasoning_content, thinking_duration_ms,
                references_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                thread_id,
                role,
                content,
                reasoning_content,
                thinking_duration_ms,
                serialized_references,
                timestamp,
            ),
        )
        await connection.execute(
            "UPDATE threads SET updated_at = ? WHERE id = ?",
            (timestamp, thread_id),
        )

    return MessageResponse(
        id=message_id,
        role=role,
        content=content,
        reasoning_content=reasoning_content,
        thinking_duration_ms=thinking_duration_ms,
        references=references or [],
    )


async def list_messages(thread_id: str) -> list[MessageResponse]:
    """按创建顺序读取会话消息，先确认会话仍然存在。"""
    await get_thread(thread_id)
    async with get_connection() as connection:
        cursor = await connection.execute(
            """
            SELECT id, role, content, reasoning_content, thinking_duration_ms, references_json
            FROM messages
            WHERE thread_id = ?
            ORDER BY created_at ASC, rowid ASC
            """,
            (thread_id,),
        )
        rows = await cursor.fetchall()
    return [_message_from_row(row) for row in rows]
