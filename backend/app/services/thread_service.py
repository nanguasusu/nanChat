from datetime import datetime, timezone
from uuid import uuid4

from app.core.database import get_connection
from app.schemas.thread import MessageResponse, ThreadResponse


class ThreadNotFoundError(LookupError):
    """Raised when a requested thread does not exist."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _thread_from_row(row) -> ThreadResponse:
    return ThreadResponse(
        id=row["id"],
        title=row["title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _message_from_row(row) -> MessageResponse:
    return MessageResponse(
        id=row["id"],
        role=row["role"],
        content=row["content"],
        reasoning_content=row["reasoning_content"],
        thinking_duration_ms=row["thinking_duration_ms"],
    )


def list_threads() -> list[ThreadResponse]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, title, created_at, updated_at FROM threads ORDER BY updated_at DESC"
        ).fetchall()
    return [_thread_from_row(row) for row in rows]


def create_thread(title: str = "New chat") -> ThreadResponse:
    thread_id = str(uuid4())
    timestamp = _now()
    normalized_title = " ".join(title.split())[:80] or "New chat"

    with get_connection() as connection:
        connection.execute(
            "INSERT INTO threads (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (thread_id, normalized_title, timestamp, timestamp),
        )

    return get_thread(thread_id)


def create_thread_with_message(title: str, content: str) -> ThreadResponse:
    """Create a new thread and its first user message in one transaction."""
    thread_id = str(uuid4())
    created_at = _now()
    message_id = str(uuid4())
    message_created_at = _now()
    normalized_title = " ".join(title.split())[:80] or "New chat"

    with get_connection() as connection:
        connection.execute(
            "INSERT INTO threads (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (thread_id, normalized_title, created_at, message_created_at),
        )
        connection.execute(
            """
            INSERT INTO messages (
                id, thread_id, role, content, reasoning_content, thinking_duration_ms, created_at
            )
            VALUES (?, ?, 'user', ?, '', 0, ?)
            """,
            (message_id, thread_id, content, message_created_at),
        )
        row = connection.execute(
            "SELECT id, title, created_at, updated_at FROM threads WHERE id = ?",
            (thread_id,),
        ).fetchone()

    return _thread_from_row(row)


def get_thread(thread_id: str) -> ThreadResponse:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, title, created_at, updated_at FROM threads WHERE id = ?",
            (thread_id,),
        ).fetchone()

    if row is None:
        raise ThreadNotFoundError(thread_id)
    return _thread_from_row(row)


def delete_thread(thread_id: str) -> None:
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM threads WHERE id = ?", (thread_id,))

    if cursor.rowcount == 0:
        raise ThreadNotFoundError(thread_id)


def update_thread_title(thread_id: str, title: str) -> ThreadResponse:
    normalized_title = " ".join(title.split())[:80] or "New chat"
    with get_connection() as connection:
        connection.execute(
            "UPDATE threads SET title = ?, updated_at = ? WHERE id = ?",
            (normalized_title, _now(), thread_id),
        )
    return get_thread(thread_id)


def add_message(
    thread_id: str,
    role: str,
    content: str,
    reasoning_content: str = "",
    thinking_duration_ms: int = 0,
    message_id: str | None = None,
) -> MessageResponse:
    message_id = message_id or str(uuid4())
    timestamp = _now()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO messages (
                id, thread_id, role, content, reasoning_content, thinking_duration_ms, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                thread_id,
                role,
                content,
                reasoning_content,
                thinking_duration_ms,
                timestamp,
            ),
        )
        connection.execute(
            "UPDATE threads SET updated_at = ? WHERE id = ?",
            (timestamp, thread_id),
        )

    return MessageResponse(
        id=message_id,
        role=role,
        content=content,
        reasoning_content=reasoning_content,
        thinking_duration_ms=thinking_duration_ms,
    )


def list_messages(thread_id: str) -> list[MessageResponse]:
    get_thread(thread_id)
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, role, content, reasoning_content, thinking_duration_ms
            FROM messages
            WHERE thread_id = ?
            ORDER BY created_at ASC, rowid ASC
            """,
            (thread_id,),
        ).fetchall()
    return [_message_from_row(row) for row in rows]
