"""调用远端 reranker，对候选 Parent 进行最终相关性排序。"""

import httpx
from pydantic import BaseModel, TypeAdapter, ValidationError

from app.core.clients import get_http_client
from app.core.config import get_rag_settings


class RerankerUnavailableError(RuntimeError):
    """重排服务不可达或返回结果无法解析时抛出。"""


class RerankResult(BaseModel):
    """reranker 返回的候选下标及相关性分数。"""

    index: int
    relevance_score: float


async def rerank_documents(
    query: str,
    documents: list[str],
    top_n: int,
) -> list[RerankResult]:
    """提交候选文本并按相关性分数从高到低返回结果。"""
    if not documents:
        return []

    settings = get_rag_settings()
    endpoint = f"{settings.embedding_base_url.rstrip('/')}/rerank"
    try:
        response = await get_http_client().post(
            endpoint,
            headers={
                "Authorization": f"Bearer {settings.embedding_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.rerank_model,
                "query": query,
                "documents": documents,
                "return_documents": False,
                "top_n": top_n,
            },
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise RerankerUnavailableError(
            "调用 SiliconFlow reranker 失败，请确认 reranker 服务配置正确。"
        ) from error

    try:
        results = TypeAdapter(list[RerankResult]).validate_python(payload["results"])
    except (KeyError, TypeError, ValidationError) as error:
        raise RerankerUnavailableError(
            "SiliconFlow reranker 返回了无法解析的结果。"
        ) from error

    if any(result.index < 0 or result.index >= len(documents) for result in results):
        raise RerankerUnavailableError(
            "SiliconFlow reranker 返回了无效的文档索引。"
        )

    return sorted(
        results,
        key=lambda result: result.relevance_score,
        reverse=True,
    )
