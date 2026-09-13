import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import get_rag_settings
from app.rag.repository import ParentChunkRecord


@dataclass(frozen=True)
class ChildChunk:
    child_id: str
    parent_id: str
    document_id: str
    content: str
    filename: str
    source: str
    page: int | None
    page_start: int | None
    page_end: int | None
    chunk_index: int


@dataclass(frozen=True)
class ChunkedDocument:
    parents: list[ParentChunkRecord]
    children: list[ChildChunk]


def _stable_id(seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return str(UUID(digest[:32]))


def _page_range(
    page_spans: list[tuple[int, int, int]],
    start: int,
    end: int,
) -> tuple[int | None, int | None]:
    if not page_spans or end <= start:
        return None, None

    pages = [
        page
        for page_start, page_end, page in page_spans
        if page_end > start and page_start < end
    ]
    return (min(pages), max(pages)) if pages else (None, None)


def _estimate_token_count(content: str) -> int:
    # The current splitter is character-based; keep this as an explicit estimate
    # until a tokenizer for the configured embedding model is introduced.
    return len(content)


def build_parent_child_chunks(
    source_documents: list[Document],
    document_id: str,
) -> ChunkedDocument:
    settings = get_rag_settings()
    if not source_documents:
        return ChunkedDocument(parents=[], children=[])

    filename = source_documents[0].metadata["filename"]
    source = source_documents[0].metadata["source"]
    joined_content = "\n".join(document.page_content for document in source_documents)

    page_spans: list[tuple[int, int, int]] = []
    cursor = 0
    for document in source_documents:
        page_content = document.page_content
        page = document.metadata["page"]
        if page is not None and page_content:
            page_spans.append((cursor, cursor + len(page_content), page))
        cursor += len(page_content) + 1

    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.parent_chunk_size,
        chunk_overlap=0,
        add_start_index=True,
    )
    parent_documents = parent_splitter.split_documents(
        [Document(page_content=joined_content)]
    )
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.child_chunk_size,
        chunk_overlap=settings.child_chunk_overlap,
    )

    parents: list[ParentChunkRecord] = []
    children: list[ChildChunk] = []
    child_index = 0
    created_at = datetime.now(timezone.utc).isoformat()
    for parent_index, parent_document in enumerate(parent_documents):
        parent_id = _stable_id(f"{document_id}:parent:{parent_index}")
        parent_start = parent_document.metadata["start_index"]
        parent_end = parent_start + len(parent_document.page_content)
        page_start, page_end = _page_range(page_spans, parent_start, parent_end)
        parents.append(
            ParentChunkRecord(
                id=parent_id,
                document_id=document_id,
                content=parent_document.page_content,
                filename=filename,
                source=source,
                page_start=page_start,
                page_end=page_end,
                chunk_index=parent_index,
                token_count=_estimate_token_count(parent_document.page_content),
                created_at=created_at,
            )
        )

        for child_document in child_splitter.split_documents([parent_document]):
            child_id = _stable_id(f"{parent_id}:child:{child_index}")
            children.append(
                ChildChunk(
                    child_id=child_id,
                    parent_id=parent_id,
                    document_id=document_id,
                    content=child_document.page_content,
                    filename=filename,
                    source=source,
                    page=page_start,
                    page_start=page_start,
                    page_end=page_end,
                    chunk_index=child_index,
                )
            )
            child_index += 1

    return ChunkedDocument(parents=parents, children=children)
