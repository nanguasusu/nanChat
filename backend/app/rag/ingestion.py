"""协调文档加载、Parent-Child 切分、SQLite 持久化和 Qdrant 建索引。"""

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
    """单个文档入库后的统计结果。"""

    document_id: str
    parent_count: int
    child_count: int


async def delete_document(document_id: str) -> None:
    """同时删除文档对应的 Qdrant Child 和 SQLite 记录。"""
    await delete_points_by_document_ids([document_id])
    await delete_documents([document_id])


async def ingest_document(path: Path) -> IngestionResult:
    """以文件内容哈希为 ID 重建一个文档，保证重复执行结果稳定。"""
    file_hash = get_file_hash(path)
    document_id = get_document_id(file_hash)
    source = str(path.resolve())
    source_documents = load_document(path)
    chunked = build_parent_child_chunks(source_documents, document_id)
    old_document_ids = [
        old_id
        for old_id in await list_document_ids_by_source(source)
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
    # 先清理旧向量和旧记录，再写入新版本，避免同一 source 残留多个版本。
    await delete_points_by_document_ids(document_ids_to_remove)
    await delete_documents(old_document_ids)

    try:
        await replace_document(document, chunked.parents)
        await index_child_chunks(chunked.children)
    except Exception:
        await delete_points_by_document_ids([document_id])
        await delete_documents([document_id])
        raise

    return IngestionResult(
        document_id=document_id,
        parent_count=len(chunked.parents),
        child_count=len(chunked.children),
    )
