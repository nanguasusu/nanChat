from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client import models
from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.core.config import RAGConfigurationError, get_rag_settings
from app.rag.chunking import ChildChunk
from app.rag.embeddings import get_embeddings


DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"
BM25_MODEL = "Qdrant/bm25"
BM25_OPTIONS = {"tokenizer": "multilingual"}
INDEX_BATCH_SIZE = 64


class KnowledgeBaseNotFoundError(RuntimeError):
    """Raised when the configured Qdrant collection has not been built."""


class KnowledgeBaseUnavailableError(RuntimeError):
    """Raised when the configured Qdrant service cannot be reached."""


def get_qdrant_client() -> QdrantClient:
    settings = get_rag_settings()
    return QdrantClient(url=settings.qdrant_url)


def _validate_hybrid_collection(client: QdrantClient) -> None:
    settings = get_rag_settings()
    collection = client.get_collection(settings.qdrant_collection)
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


def get_existing_qdrant_client() -> QdrantClient:
    settings = get_rag_settings()
    client = get_qdrant_client()
    try:
        collection_exists = client.collection_exists(settings.qdrant_collection)
    except Exception as error:
        raise KnowledgeBaseUnavailableError(
            "无法连接 Qdrant，请确认 Qdrant 正在运行且 QDRANT_URL 配置正确。"
        ) from error

    if not collection_exists:
        raise KnowledgeBaseNotFoundError(
            f"知识库 collection '{settings.qdrant_collection}' 不存在，请先运行 build_kb.py。"
        )

    try:
        _validate_hybrid_collection(client)
    except KnowledgeBaseUnavailableError:
        raise
    except Exception as error:
        raise KnowledgeBaseUnavailableError(
            "读取 Qdrant collection 失败，请确认 collection 配置与 embedding 模型一致。"
        ) from error
    return client


def _ensure_hybrid_collection(
    client: QdrantClient,
    dense_vector_size: int,
) -> None:
    settings = get_rag_settings()
    if not client.collection_exists(settings.qdrant_collection):
        client.create_collection(
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
        return

    _validate_hybrid_collection(client)
    collection = client.get_collection(settings.qdrant_collection)
    dense_vector = collection.config.params.vectors[DENSE_VECTOR_NAME]
    if dense_vector.size != dense_vector_size:
        raise KnowledgeBaseUnavailableError(
            "Qdrant dense 向量维度与当前 embedding 模型不一致，请运行 build_kb.py --rebuild。"
        )


def index_child_chunks(children: list[ChildChunk]) -> int:
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
        dense_vectors = embeddings.embed_documents(
            [document.page_content for document in documents]
        )
        _ensure_hybrid_collection(client, len(dense_vectors[0]))
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
            client.upsert(
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


def delete_points_by_document_ids(document_ids: list[str]) -> None:
    if not document_ids:
        return

    settings = get_rag_settings()
    client = get_qdrant_client()
    try:
        if not client.collection_exists(settings.qdrant_collection):
            return
        client.delete(
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


def delete_collection() -> None:
    settings = get_rag_settings()
    client = get_qdrant_client()
    try:
        if client.collection_exists(settings.qdrant_collection):
            client.delete_collection(settings.qdrant_collection)
    except Exception as error:
        raise KnowledgeBaseUnavailableError(
            "删除 Qdrant collection 失败，请确认 Qdrant 正在运行。"
        ) from error
