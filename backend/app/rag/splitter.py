"""旧版单层切分工具，保留供兼容调用方使用。"""

import hashlib
from uuid import UUID

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import get_rag_settings


def split_documents(documents: list[Document]) -> list[Document]:
    """按配置切分文档，并为每个片段补充稳定索引和 UUID。"""
    settings = get_rag_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    chunks = splitter.split_documents(documents)

    next_chunk_index: dict[str, int] = {}
    for chunk in chunks:
        document_id = chunk.metadata["document_id"]
        chunk_index = next_chunk_index.get(document_id, 0)
        chunk_hash = hashlib.sha256(
            f"{document_id}:{chunk_index}".encode("utf-8")
        ).hexdigest()
        chunk_id = str(UUID(chunk_hash[:32]))
        chunk.metadata = {
            **chunk.metadata,
            "chunk_index": chunk_index,
            "chunk_id": chunk_id,
        }
        next_chunk_index[document_id] = chunk_index + 1

    return chunks
