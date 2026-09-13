from dataclasses import dataclass

from app.core.database import get_connection


@dataclass(frozen=True)
class DocumentRecord:
    id: str
    filename: str
    source: str
    file_hash: str
    parser: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ParentChunkRecord:
    id: str
    document_id: str
    content: str
    filename: str
    source: str
    page_start: int | None
    page_end: int | None
    chunk_index: int
    token_count: int | None
    created_at: str


def list_document_ids_by_source(source: str) -> list[str]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id FROM documents WHERE source = ?",
            (source,),
        ).fetchall()
    return [row["id"] for row in rows]


def replace_document(
    document: DocumentRecord,
    parent_chunks: list[ParentChunkRecord],
) -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM documents WHERE id = ?", (document.id,))
        connection.execute(
            """
            INSERT INTO documents (
                id, filename, source, file_hash, parser, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document.id,
                document.filename,
                document.source,
                document.file_hash,
                document.parser,
                document.created_at,
                document.updated_at,
            ),
        )
        connection.executemany(
            """
            INSERT INTO parent_chunks (
                id, document_id, content, page_start, page_end,
                chunk_index, token_count, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    chunk.id,
                    chunk.document_id,
                    chunk.content,
                    chunk.page_start,
                    chunk.page_end,
                    chunk.chunk_index,
                    chunk.token_count,
                    chunk.created_at,
                )
                for chunk in parent_chunks
            ],
        )


def delete_documents(document_ids: list[str]) -> None:
    if not document_ids:
        return

    placeholders = ", ".join("?" for _ in document_ids)
    with get_connection() as connection:
        connection.execute(
            f"DELETE FROM documents WHERE id IN ({placeholders})",
            document_ids,
        )


def clear_knowledge_base() -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM documents")


def get_parent_chunks(parent_ids: list[str]) -> list[ParentChunkRecord]:
    if not parent_ids:
        return []

    placeholders = ", ".join("?" for _ in parent_ids)
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT parent_chunks.id, parent_chunks.document_id, parent_chunks.content,
                   documents.filename, documents.source, parent_chunks.page_start,
                   parent_chunks.page_end, parent_chunks.chunk_index,
                   parent_chunks.token_count, parent_chunks.created_at
            FROM parent_chunks
            JOIN documents ON documents.id = parent_chunks.document_id
            WHERE parent_chunks.id IN ({placeholders})
            """,
            parent_ids,
        ).fetchall()

    return [
        ParentChunkRecord(
            id=row["id"],
            document_id=row["document_id"],
            content=row["content"],
            filename=row["filename"],
            source=row["source"],
            page_start=row["page_start"],
            page_end=row["page_end"],
            chunk_index=row["chunk_index"],
            token_count=row["token_count"],
            created_at=row["created_at"],
        )
        for row in rows
    ]
