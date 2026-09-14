"""提供 SQLite 连接上下文和应用启动时的数据库初始化。"""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "ai_chat.db"
DATABASE_PATH = Path(os.getenv("SQLITE_DB_PATH", str(DEFAULT_DATABASE_PATH)))

_SCHEMA = """
            CREATE TABLE IF NOT EXISTS threads (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                reasoning_content TEXT NOT NULL DEFAULT '',
                thinking_duration_ms INTEGER NOT NULL DEFAULT 0,
                references_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                FOREIGN KEY (thread_id) REFERENCES threads (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                source TEXT,
                file_hash TEXT,
                parser TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS parent_chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                content TEXT NOT NULL,
                page_start INTEGER,
                page_end INTEGER,
                chunk_index INTEGER NOT NULL,
                token_count INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_thread_created_at
                ON messages (thread_id, created_at);

            CREATE INDEX IF NOT EXISTS idx_parent_chunks_document_id
                ON parent_chunks (document_id);

            CREATE INDEX IF NOT EXISTS idx_parent_chunks_document_chunk_index
                ON parent_chunks (document_id, chunk_index);
            """


@asynccontextmanager
async def get_connection() -> AsyncIterator[aiosqlite.Connection]:
    """创建带事务边界的 SQLite 连接，成功提交、异常回滚。"""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = await aiosqlite.connect(DATABASE_PATH)
    connection.row_factory = aiosqlite.Row
    await connection.execute("PRAGMA foreign_keys = ON")
    await connection.execute("PRAGMA journal_mode = WAL")
    await connection.execute("PRAGMA busy_timeout = 5000")
    try:
        yield connection
        await connection.commit()
    except Exception:
        await connection.rollback()
        raise
    finally:
        await connection.close()


async def init_database() -> None:
    """创建当前版本所需的表和索引，并补齐旧库新增字段。"""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with get_connection() as connection:
        await connection.executescript(_SCHEMA)

        cursor = await connection.execute("PRAGMA table_info(messages)")
        message_columns = {row["name"] for row in await cursor.fetchall()}
        if "reasoning_content" not in message_columns:
            await connection.execute(
                "ALTER TABLE messages ADD COLUMN reasoning_content TEXT NOT NULL DEFAULT ''"
            )
        if "thinking_duration_ms" not in message_columns:
            await connection.execute(
                "ALTER TABLE messages ADD COLUMN thinking_duration_ms INTEGER NOT NULL DEFAULT 0"
            )
        if "references_json" not in message_columns:
            await connection.execute(
                "ALTER TABLE messages ADD COLUMN references_json TEXT NOT NULL DEFAULT '[]'"
            )
