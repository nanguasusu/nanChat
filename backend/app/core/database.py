import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv

load_dotenv()

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "ai_chat.db"
DATABASE_PATH = Path(os.getenv("SQLITE_DB_PATH", str(DEFAULT_DATABASE_PATH)))


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_database() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
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
                created_at TEXT NOT NULL,
                FOREIGN KEY (thread_id) REFERENCES threads (id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_thread_created_at
                ON messages (thread_id, created_at);
            """
        )

        message_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(messages)").fetchall()
        }
        if "reasoning_content" not in message_columns:
            connection.execute(
                "ALTER TABLE messages ADD COLUMN reasoning_content TEXT NOT NULL DEFAULT ''"
            )
        if "thinking_duration_ms" not in message_columns:
            connection.execute(
                "ALTER TABLE messages ADD COLUMN thinking_duration_ms INTEGER NOT NULL DEFAULT 0"
            )
