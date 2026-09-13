from langchain_openai import OpenAIEmbeddings

from app.core.config import get_rag_settings


def get_embeddings() -> OpenAIEmbeddings:
    """Create the single embedding implementation shared by indexing and search."""
    settings = get_rag_settings()
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.embedding_api_key,
        base_url=settings.embedding_base_url,
        check_embedding_ctx_length=False,
    )
