import logging
from dataclasses import dataclass

from qdrant_client import models

from app.core.config import RAGConfigurationError, get_rag_settings
from app.rag.embeddings import get_embeddings
from app.rag.repository import get_parent_chunks
from app.rag.reranker import RerankerUnavailableError, rerank_documents
from app.rag.schemas import RetrievedParent
from app.rag.vectorstore import (
    BM25_MODEL,
    BM25_OPTIONS,
    DENSE_VECTOR_NAME,
    KnowledgeBaseNotFoundError,
    KnowledgeBaseUnavailableError,
    SPARSE_VECTOR_NAME,
    get_existing_qdrant_client,
)

logger = logging.getLogger(__name__)


@dataclass
class ParentCandidate:
    parent_id: str
    max_score: float
    hit_count: int
    matched_child_ids: list[str]


async def retrieve(query: str, parent_top_k: int | None = None) -> list[RetrievedParent]:
    try:
        settings = get_rag_settings()
        if parent_top_k is None:
            parent_top_k = settings.rerank_parent_top_k
        client = get_existing_qdrant_client()
        embeddings = get_embeddings()
        dense_query = await embeddings.aembed_query(query)
        response = client.query_points(
            collection_name=settings.qdrant_collection,
            prefetch=[
                models.Prefetch(
                    query=dense_query,
                    using=DENSE_VECTOR_NAME,
                    limit=settings.dense_retrieval_top_k,
                ),
                models.Prefetch(
                    query=models.Document(
                        text=query,
                        model=BM25_MODEL,
                        options=BM25_OPTIONS,
                    ),
                    using=SPARSE_VECTOR_NAME,
                    limit=settings.sparse_retrieval_top_k,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=settings.retrieval_child_top_k,
            with_payload=True,
        )
        matches = response.points
    except (
        RAGConfigurationError,
        KnowledgeBaseNotFoundError,
        KnowledgeBaseUnavailableError,
    ):
        raise
    except Exception as error:
        raise KnowledgeBaseUnavailableError(
            "检索知识库失败，请确认 Qdrant 正在运行且 embedding 服务配置正确。"
        ) from error

    candidates: dict[str, ParentCandidate] = {}
    for match in matches:
        metadata = match.payload["metadata"]
        parent_id = metadata["parent_id"]
        child_id = metadata["child_id"]
        score = match.score
        candidate = candidates.get(parent_id)
        if candidate is None:
            candidates[parent_id] = ParentCandidate(
                parent_id=parent_id,
                max_score=score,
                hit_count=1,
                matched_child_ids=[child_id],
            )
            continue

        candidate.max_score = max(candidate.max_score, score)
        candidate.hit_count += 1
        candidate.matched_child_ids.append(child_id)

    ranked_candidates = sorted(
        candidates.values(),
        key=lambda candidate: candidate.max_score,
        reverse=True,
    )
    rerank_candidates = ranked_candidates[: settings.rerank_candidate_top_k]
    parents = get_parent_chunks([candidate.parent_id for candidate in rerank_candidates])
    parents_by_id = {parent.id: parent for parent in parents}
    candidate_parents = [
        (candidate, parents_by_id[candidate.parent_id])
        for candidate in rerank_candidates
    ]
    try:
        reranked = await rerank_documents(
            query,
            [parent.content for _, parent in candidate_parents],
            top_n=min(parent_top_k, len(candidate_parents)),
        )
    except RerankerUnavailableError as error:
        raise KnowledgeBaseUnavailableError(str(error)) from error
    reranked = [
        result
        for result in reranked
        if result.relevance_score >= settings.rerank_min_score
    ]
    logger.info(
        "RAG retrieval: child_hits=%d unique_parents=%d rerank_candidates=%d parents_after_threshold=%d threshold=%.3f",
        len(matches),
        len(ranked_candidates),
        len(candidate_parents),
        len(reranked),
        settings.rerank_min_score,
    )

    results: list[RetrievedParent] = []
    for rerank_result in reranked:
        candidate, parent = candidate_parents[rerank_result.index]
        results.append(
            RetrievedParent(
                parent_id=parent.id,
                document_id=parent.document_id,
                content=parent.content,
                filename=parent.filename,
                source=parent.source,
                page_start=parent.page_start,
                page_end=parent.page_end,
                score=rerank_result.relevance_score,
                hit_count=candidate.hit_count,
                matched_child_ids=candidate.matched_child_ids,
            )
        )
    return results
