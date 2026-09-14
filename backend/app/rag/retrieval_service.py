"""执行混合检索、Parent 聚合、重排和短期语义缓存。"""

import asyncio
import logging
from dataclasses import dataclass

from qdrant_client import models

from app.core.config import RAGConfigurationError, RAGSettings, get_rag_settings
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

SEMANTIC_CACHE_THRESHOLD = 0.92
SEMANTIC_CACHE_SIZE = 64


@dataclass
class ParentCandidate:
    """由多个 Child 命中聚合出的 Parent 候选统计。"""

    parent_id: str
    max_score: float
    hit_count: int
    matched_child_ids: list[str]


@dataclass
class _CacheEntry:
    """一次已完成检索的 query、向量和结果缓存。"""

    query: str
    embedding: list[float]
    parent_top_k: int
    results: list[RetrievedParent]


_cache: list[_CacheEntry] = []
_cache_lock = asyncio.Lock()


def clear_retrieval_cache() -> None:
    """清空进程内检索缓存，便于知识库更新后立即使用新结果。"""
    _cache.clear()


def _normalize_query(query: str) -> str:
    """统一空白字符，提升相同问题的精确缓存命中率。"""
    return " ".join(query.split())


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    """计算两条向量的余弦相似度，用于近似 query 缓存复用。"""
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm_left = sum(a * a for a in left) ** 0.5
    norm_right = sum(b * b for b in right) ** 0.5
    if norm_left == 0 or norm_right == 0:
        return 0.0
    return dot / (norm_left * norm_right)


def _lookup_exact(query: str, parent_top_k: int) -> _CacheEntry | None:
    """按规范化 query 和返回数量查找精确缓存。"""
    for entry in reversed(_cache):
        if entry.query == query and entry.parent_top_k == parent_top_k:
            return entry
    return None


def _lookup_semantic(
    embedding: list[float], parent_top_k: int
) -> tuple[_CacheEntry, float] | None:
    """在同一 top-k 配置下查找足够相似的历史 query。"""
    best: _CacheEntry | None = None
    best_score = SEMANTIC_CACHE_THRESHOLD
    for entry in _cache:
        if entry.parent_top_k != parent_top_k:
            continue
        score = _cosine_similarity(embedding, entry.embedding)
        if score >= best_score:
            best = entry
            best_score = score
    return (best, best_score) if best is not None else None


def _store_cache(
    query: str,
    embedding: list[float],
    parent_top_k: int,
    results: list[RetrievedParent],
) -> None:
    """追加检索结果并维持固定大小的先进先出缓存。"""
    _cache.append(
        _CacheEntry(
            query=query,
            embedding=embedding,
            parent_top_k=parent_top_k,
            results=list(results),
        )
    )
    overflow = len(_cache) - SEMANTIC_CACHE_SIZE
    if overflow > 0:
        del _cache[:overflow]


async def retrieve(query: str, parent_top_k: int | None = None) -> list[RetrievedParent]:
    """检索并返回最终 Parent；支持精确和语义两级缓存。"""
    settings = get_rag_settings()
    if parent_top_k is None:
        parent_top_k = settings.rerank_parent_top_k
    normalized = _normalize_query(query)

    async with _cache_lock:
        exact = _lookup_exact(normalized, parent_top_k)
        if exact is not None:
            logger.info("RAG retrieval cache: exact hit query=%r", normalized)
            return list(exact.results)

    try:
        dense_query = await get_embeddings().aembed_query(query)
    except RAGConfigurationError:
        raise
    except Exception as error:
        raise KnowledgeBaseUnavailableError(
            "检索知识库失败，请确认 Qdrant 正在运行且 embedding 服务配置正确。"
        ) from error

    async with _cache_lock:
        semantic = _lookup_semantic(dense_query, parent_top_k)
        if semantic is not None:
            entry, score = semantic
            logger.info(
                "RAG retrieval cache: semantic hit sim=%.3f query=%r cached=%r",
                score,
                normalized,
                entry.query,
            )
            return list(entry.results)

    results = await _search_knowledge_base(
        query, dense_query, settings, parent_top_k
    )
    async with _cache_lock:
        _store_cache(normalized, dense_query, parent_top_k, results)
    return results


async def _search_knowledge_base(
    query: str,
    dense_query: list[float],
    settings: RAGSettings,
    parent_top_k: int,
) -> list[RetrievedParent]:
    """用 dense+BM25 子片段检索，再聚合 Parent 并执行 reranker 过滤。"""
    try:
        client = await get_existing_qdrant_client()
        response = await client.query_points(
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

    # Qdrant 返回的是 Child 命中，先按 parent_id 合并，避免上下文碎片化。
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
    parents = await get_parent_chunks(
        [candidate.parent_id for candidate in rerank_candidates]
    )
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
    # 阈值只作用于 reranker 分数，不与 Qdrant 的 RRF 分数混用。
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
