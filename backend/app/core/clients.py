"""按需创建并复用外部服务客户端，在应用关闭时统一释放。"""

import httpx
from openai import AsyncOpenAI, DefaultAsyncHttpxClient
from qdrant_client import AsyncQdrantClient

from app.core.config import LongCatSettings, get_longcat_settings, get_rag_settings

_longcat_client: AsyncOpenAI | None = None
_http_client: httpx.AsyncClient | None = None
_qdrant_client: AsyncQdrantClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """返回用于重排请求的共享 HTTP 客户端。"""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=30.0, trust_env=False)
    return _http_client


def get_longcat_client(settings: LongCatSettings | None = None) -> AsyncOpenAI:
    """返回共享的 OpenAI 兼容客户端；可传入本次请求解析出的配置。"""
    global _longcat_client
    if _longcat_client is None:
        resolved = settings or get_longcat_settings()
        _longcat_client = AsyncOpenAI(
            api_key=resolved.api_key,
            base_url=resolved.base_url,
            http_client=DefaultAsyncHttpxClient(trust_env=False),
        )
    return _longcat_client


def get_qdrant_client() -> AsyncQdrantClient:
    """返回连接当前知识库 collection 的共享 Qdrant 客户端。"""
    global _qdrant_client
    if _qdrant_client is None:
        settings = get_rag_settings()
        _qdrant_client = AsyncQdrantClient(url=settings.qdrant_url)
    return _qdrant_client


async def close_clients() -> None:
    """关闭所有已创建的客户端，并清空缓存引用。"""
    global _longcat_client, _http_client, _qdrant_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
    if _longcat_client is not None:
        await _longcat_client.close()
        _longcat_client = None
    if _qdrant_client is not None:
        await _qdrant_client.close()
        _qdrant_client = None
