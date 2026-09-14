"""管理 Qdrant 混合向量 collection 及 Child 的索引生命周期。"""

from langchain_core.documents import Document
from qdrant_client import models
from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.core.clients import get_qdrant_client
from app.core.config import RAGConfigurationError, get_rag_settings
from app.rag.chunking import ChildChunk
from app.rag.embeddings import get_embeddings


DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"
BM25_MODEL = "Qdrant/bm25"
BM25_OPTIONS = {"tokenizer": "multilingual"}
INDEX_BATCH_SIZE = 64

_validated_collection: str | None = None


class KnowledgeBaseNotFoundError(RuntimeError):
    """配置的 Qdrant collection 尚未创建时抛出。"""


class KnowledgeBaseUnavailableError(RuntimeError):
    """Qdrant 不可达或 collection 结构不兼容时抛出。"""


def reset_qdrant_validation() -> None:
    """清除 collection 结构校验缓存，使下一次访问重新校验。"""
    global _validated_collection
    _validated_collection = None


async def _validate_hybrid_collection() -> None:
    """确认 collection 同时包含 dense 和 BM25 sparse 两种向量。"""
    settings = get_rag_settings()
    client = get_qdrant_client()
    collection = await client.get_collection(settings.qdrant_collection)
    params = collection.config.params
    vectors = params.vectors
    sparse_vectors = params.sparse_vectors
    if (
        not isinstance(vectors, dict)
        or set(vectors) != {DENSE_VECTOR_NAME}
        or not isinstance(sparse_vectors, dict)
        or SPARSE_VECTOR_NAME not in sparse_vectors
    ):
        raise KnowledgeBaseUnavailableError(
            "Qdrant collection 不是 dense+sparse 混合向量结构，请运行 build_kb.py --rebuild。"
        )


async def get_existing_qdrant_client():
    """返回已构建且结构兼容的 collection 客户端。"""
    global _validated_collection
    settings = get_rag_settings()
    client = get_qdrant_client()
    if _validated_collection == settings.qdrant_collection:
        return client

    try:
        collection_exists = await client.collection_exists(settings.qdrant_collection)
    except Exception as error:
        raise KnowledgeBaseUnavailableError(
            "无法连接 Qdrant，请确认 Qdrant 正在运行且 QDRANT_URL 配置正确。"
        ) from error

    if not collection_exists:
        raise KnowledgeBaseNotFoundError(
            f"知识库 collection '{settings.qdrant_collection}' 不存在，请先运行 build_kb.py。"
        )

    try:
        await _validate_hybrid_collection()
    except KnowledgeBaseUnavailableError:
        raise
    except Exception as error:
        raise KnowledgeBaseUnavailableError(
            "读取 Qdrant collection 失败，请确认 collection 配置与 embedding 模型一致。"
        ) from error

    _validated_collection = settings.qdrant_collection
    return client


async def _ensure_hybrid_collection(dense_vector_size: int) -> None:
    """按当前 embedding 维度创建 collection，或校验已有 collection。"""
    settings = get_rag_settings()
    client = get_qdrant_client()
    if not await client.collection_exists(settings.qdrant_collection):
        await client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config={
                DENSE_VECTOR_NAME: models.VectorParams(
                    size=dense_vector_size,
                    distance=models.Distance.COSINE,
                )
            },
            sparse_vectors_config={
                SPARSE_VECTOR_NAME: models.SparseVectorParams(
                    modifier=models.Modifier.IDF,
                )
            },
        )
        reset_qdrant_validation()
        return

    await _validate_hybrid_collection()
    collection = await client.get_collection(settings.qdrant_collection)
    dense_vector = collection.config.params.vectors[DENSE_VECTOR_NAME]
    if dense_vector.size != dense_vector_size:
        raise KnowledgeBaseUnavailableError(
            "Qdrant dense 向量维度与当前 embedding 模型不一致，请运行 build_kb.py --rebuild。"
        )


async def index_child_chunks(children: list[ChildChunk]) -> int:
    """批量生成 Child 向量并写入 Qdrant。"""
    if not children:
        return 0

    settings = get_rag_settings()
    client = get_qdrant_client()
    embeddings = get_embeddings()
    documents = [
        Document(
            page_content=child.content,
            metadata={
                "child_id": child.child_id,
                "parent_id": child.parent_id,
                "document_id": child.document_id,
                "filename": child.filename,
                "source": child.source,
                "page": child.page,
                "page_start": child.page_start,
                "page_end": child.page_end,
                "chunk_index": child.chunk_index,
            },
        )
        for child in children
    ]

    try:
        # Embedding 分批请求，Qdrant 写入也分批进行，避免单次 payload 过大。
        dense_vectors: list[list[float]] = []
        texts = [document.page_content for document in documents]
        for start in range(0, len(texts), INDEX_BATCH_SIZE):
            dense_vectors.extend(
                await embeddings.aembed_documents(texts[start : start + INDEX_BATCH_SIZE])
            )
        await _ensure_hybrid_collection(len(dense_vectors[0]))
        points = [
            models.PointStruct(
                id=child.child_id,
                vector={
                    DENSE_VECTOR_NAME: dense_vector,
                    SPARSE_VECTOR_NAME: models.Document(
                        text=child.content,
                        model=BM25_MODEL,
                        options=BM25_OPTIONS,
                    ),
                },
                payload={
                    "content": child.content,
                    "metadata": document.metadata,
                },
            )
            for child, dense_vector, document in zip(
                children,
                dense_vectors,
                documents,
                strict=True,
            )
        ]
        for start in range(0, len(points), INDEX_BATCH_SIZE):
            await client.upsert(
                collection_name=settings.qdrant_collection,
                points=points[start : start + INDEX_BATCH_SIZE],
            )
    except RAGConfigurationError:
        raise
    except Exception as error:
        raise KnowledgeBaseUnavailableError(
            "写入 Qdrant 失败，请确认 Qdrant 正在运行且 embedding 服务配置正确。"
        ) from error

    return len(documents)


async def delete_points_by_document_ids(document_ids: list[str]) -> None:
    """删除指定文档产生的全部 Child points。"""
    if not document_ids:
        return

    settings = get_rag_settings()
    client = get_qdrant_client()
    try:
        if not await client.collection_exists(settings.qdrant_collection):
            return
        await client.delete(
            collection_name=settings.qdrant_collection,
            points_selector=Filter(
                should=[
                    FieldCondition(
                        key="metadata.document_id",
                        match=MatchValue(value=document_id),
                    )
                    for document_id in document_ids
                ]
            ),
        )
    except Exception as error:
        raise KnowledgeBaseUnavailableError(
            "删除 Qdrant Child Points 失败，请确认 Qdrant 正在运行。"
        ) from error


async def delete_collection() -> None:
    """删除当前知识库 collection，并使结构校验缓存失效。"""
    settings = get_rag_settings()
    client = get_qdrant_client()
    try:
        if await client.collection_exists(settings.qdrant_collection):
            await client.delete_collection(settings.qdrant_collection)
        reset_qdrant_validation()
    except Exception as error:
        raise KnowledgeBaseUnavailableError(
            "删除 Qdrant collection 失败，请确认 Qdrant 正在运行。"
        ) from error
