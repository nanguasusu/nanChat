"""创建并复用 OpenAI 兼容的文本向量模型。"""

from langchain_openai import OpenAIEmbeddings

from app.core.config import get_rag_settings

_embeddings: OpenAIEmbeddings | None = None


def get_embeddings() -> OpenAIEmbeddings:
    """返回索引与检索共用的单例向量模型。"""
    global _embeddings
    if _embeddings is None:
        settings = get_rag_settings()
        _embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.embedding_api_key,
            base_url=settings.embedding_base_url,
            check_embedding_ctx_length=False,
        )
    return _embeddings
