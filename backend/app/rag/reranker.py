import httpx
from pydantic import BaseModel, TypeAdapter, ValidationError

from app.core.config import get_rag_settings


class RerankerUnavailableError(RuntimeError):
    """Raised when the configured reranker cannot be reached or parsed."""


class RerankResult(BaseModel):
    index: int
    relevance_score: float


async def rerank_documents(
    query: str,
    documents: list[str],
    top_n: int,
) -> list[RerankResult]:
    if not documents:
        return []

    settings = get_rag_settings()
    endpoint = f"{settings.embedding_base_url.rstrip('/')}/rerank"
    try:
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            response = await client.post(
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
