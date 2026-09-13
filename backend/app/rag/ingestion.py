from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.rag.chunking import build_parent_child_chunks
from app.rag.loader import get_document_id, get_file_hash, load_document
from app.rag.repository import (
    DocumentRecord,
    delete_documents,
    list_document_ids_by_source,
    replace_document,
)
from app.rag.vectorstore import (
    delete_points_by_document_ids,
    index_child_chunks,
)


@dataclass(frozen=True)
class IngestionResult:
    document_id: str
    parent_count: int
    child_count: int


def delete_document(document_id: str) -> None:
    delete_points_by_document_ids([document_id])
    delete_documents([document_id])


def ingest_document(path: Path) -> IngestionResult:
    file_hash = get_file_hash(path)
    document_id = get_document_id(file_hash)
    source = str(path.resolve())
    source_documents = load_document(path)
    chunked = build_parent_child_chunks(source_documents, document_id)
    old_document_ids = [
        old_id
        for old_id in list_document_ids_by_source(source)
        if old_id != document_id
    ]
    document_timestamp = datetime.now(timezone.utc).isoformat()
    document = DocumentRecord(
        id=document_id,
        filename=path.name,
        source=source,
        file_hash=file_hash,
        parser="pypdf" if path.suffix.lower() == ".pdf" else "text",
        created_at=document_timestamp,
        updated_at=document_timestamp,
    )

    document_ids_to_remove = [*old_document_ids, document_id]
    delete_points_by_document_ids(document_ids_to_remove)
    delete_documents(old_document_ids)

    try:
        replace_document(document, chunked.parents)
        index_child_chunks(chunked.children)
    except Exception:
        delete_points_by_document_ids([document_id])
        delete_documents([document_id])
        raise

    return IngestionResult(
        document_id=document_id,
        parent_count=len(chunked.parents),
        child_count=len(chunked.children),
    )
