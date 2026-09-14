"""集中读取并校验模型、知识库和 Agentic RAG 的运行配置。"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


class LongCatConfigurationError(RuntimeError):
    """模型服务配置缺失或无效时抛出。"""


@dataclass(frozen=True)
class LongCatSettings:
    """调用对话模型所需的连接参数。"""

    api_key: str
    base_url: str
    model: str


class RAGConfigurationError(RuntimeError):
    """知识库相关配置缺失或无效时抛出。"""


@dataclass(frozen=True)
class RAGSettings:
    """知识库切分、检索、重排和向量服务的配置。"""

    qdrant_url: str
    qdrant_collection: str
    parent_chunk_size: int
    child_chunk_size: int
    child_chunk_overlap: int
    dense_retrieval_top_k: int
    sparse_retrieval_top_k: int
    retrieval_child_top_k: int
    rerank_candidate_top_k: int
    rerank_parent_top_k: int
    rerank_min_score: float
    rerank_model: str
    embedding_model: str
    embedding_base_url: str
    embedding_api_key: str


@dataclass(frozen=True)
class AgenticRAGSettings:
    """Agentic RAG 的任务数量、重试次数和并发限制。"""

    max_plan_tasks: int
    max_scope_tasks: int
    task_max_retrievals: int
    max_concurrency: int


DEFAULT_MODEL = "glm-5.3-flash"
DEFAULT_CONTEXT_WINDOW_TOKENS = 1_048_576
DEFAULT_PARENT_CHUNK_SIZE = 1600
DEFAULT_CHILD_CHUNK_SIZE = 400
DEFAULT_CHILD_CHUNK_OVERLAP = 80
DEFAULT_DENSE_RETRIEVAL_TOP_K = 20
DEFAULT_SPARSE_RETRIEVAL_TOP_K = 20
DEFAULT_RETRIEVAL_CHILD_TOP_K = 30
DEFAULT_RERANK_CANDIDATE_TOP_K = 12
DEFAULT_RERANK_PARENT_TOP_K = 4
DEFAULT_RERANK_MIN_SCORE = 0.4
DEFAULT_RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
MAX_RAG_TOP_K = 50
DEFAULT_AGENTIC_MAX_PLAN_TASKS = 4
DEFAULT_AGENTIC_MAX_SCOPE_TASKS = 3
DEFAULT_AGENTIC_TASK_MAX_RETRIEVALS = 2
DEFAULT_AGENTIC_MAX_CONCURRENCY = 3


def get_configured_model() -> str:
    """返回环境变量指定的模型名；未配置时使用默认模型。"""
    return os.getenv("LONGCAT_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def get_context_window_tokens() -> int:
    """读取前端展示用的模型上下文窗口大小。"""
    return int(
        os.getenv(
            "LONGCAT_CONTEXT_WINDOW_TOKENS",
            str(DEFAULT_CONTEXT_WINDOW_TOKENS),
        )
    )


def get_cors_origins() -> list[str]:
    """把逗号分隔的跨域来源整理为非空列表。"""
    configured_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    return [origin.strip() for origin in configured_origins.split(",") if origin.strip()]


def get_longcat_settings() -> LongCatSettings:
    """读取并校验对话模型的 API 配置。"""
    api_key = os.getenv("LONGCAT_API_KEY", "").strip()
    if not api_key or api_key in {
        "replace-with-your-local-api-key",
        "replace-with-your-zai-api-key",
    }:
        raise LongCatConfigurationError(
            "LONGCAT_API_KEY is not configured. Add it to backend/.env before sending chat messages."
        )

    return LongCatSettings(
        api_key=api_key,
        base_url=os.getenv("LONGCAT_BASE_URL", "https://api.z.ai/api/paas/v4/"),
        model=get_configured_model(),
    )


def get_agentic_rag_settings() -> AgenticRAGSettings:
    """读取 Agentic RAG 限制，并确保其处于当前版本支持的范围内。"""
    try:
        settings = AgenticRAGSettings(
            max_plan_tasks=int(
                os.getenv("AGENTIC_MAX_PLAN_TASKS", str(DEFAULT_AGENTIC_MAX_PLAN_TASKS))
            ),
            max_scope_tasks=int(
                os.getenv("AGENTIC_MAX_SCOPE_TASKS", str(DEFAULT_AGENTIC_MAX_SCOPE_TASKS))
            ),
            task_max_retrievals=int(
                os.getenv(
                    "AGENTIC_TASK_MAX_RETRIEVALS",
                    str(DEFAULT_AGENTIC_TASK_MAX_RETRIEVALS),
                )
            ),
            max_concurrency=int(
                os.getenv(
                    "AGENTIC_MAX_CONCURRENCY",
                    str(DEFAULT_AGENTIC_MAX_CONCURRENCY),
                )
            ),
        )
    except ValueError as error:
        raise RAGConfigurationError("Agentic RAG settings must be valid integers.") from error

    if (
        not 1 <= settings.max_plan_tasks <= 4
        or not 1 <= settings.max_scope_tasks <= 3
        or not 1 <= settings.task_max_retrievals <= 2
        or not 1 <= settings.max_concurrency <= 3
    ):
        raise RAGConfigurationError(
            "Agentic RAG limits exceed the supported v1 bounds."
        )
    return settings


def get_rag_settings() -> RAGSettings:
    """读取并校验 Parent-Child RAG 的全部运行参数。"""
    embedding_api_key = os.getenv("EMBEDDING_API_KEY", "").strip()
    if not embedding_api_key or embedding_api_key == "replace-with-your-local-api-key":
        raise RAGConfigurationError(
            "EMBEDDING_API_KEY is not configured. Add the embedding service key to backend/.env."
        )

    try:
        parent_chunk_size = int(
            os.getenv("PARENT_CHUNK_SIZE", str(DEFAULT_PARENT_CHUNK_SIZE))
        )
        child_chunk_size = int(
            os.getenv("CHILD_CHUNK_SIZE", str(DEFAULT_CHILD_CHUNK_SIZE))
        )
        child_chunk_overlap = int(
            os.getenv("CHILD_CHUNK_OVERLAP", str(DEFAULT_CHILD_CHUNK_OVERLAP))
        )
        dense_retrieval_top_k = int(
            os.getenv(
                "DENSE_RETRIEVAL_TOP_K",
                str(DEFAULT_DENSE_RETRIEVAL_TOP_K),
            )
        )
        sparse_retrieval_top_k = int(
            os.getenv(
                "SPARSE_RETRIEVAL_TOP_K",
                str(DEFAULT_SPARSE_RETRIEVAL_TOP_K),
            )
        )
        retrieval_child_top_k = int(
            os.getenv(
                "RETRIEVAL_CHILD_TOP_K",
                str(DEFAULT_RETRIEVAL_CHILD_TOP_K),
            )
        )
        rerank_candidate_top_k = int(
            os.getenv(
                "RERANK_CANDIDATE_TOP_K",
                str(DEFAULT_RERANK_CANDIDATE_TOP_K),
            )
        )
        rerank_parent_top_k = int(
            os.getenv(
                "RERANK_PARENT_TOP_K",
                str(DEFAULT_RERANK_PARENT_TOP_K),
            )
        )
        rerank_min_score = float(
            os.getenv("RERANK_MIN_SCORE", str(DEFAULT_RERANK_MIN_SCORE))
        )
    except ValueError as error:
        raise RAGConfigurationError(
            "Parent-Child chunk and retrieval settings must be valid numbers."
        ) from error

    if (
        parent_chunk_size <= 0
        or child_chunk_size <= 0
        or child_chunk_overlap < 0
        or child_chunk_overlap >= child_chunk_size
        or child_chunk_size >= parent_chunk_size
    ):
        raise RAGConfigurationError(
            "Parent and child chunk sizes are invalid. Child overlap must be between 0 and child size, and child size must be smaller than parent size."
        )
    if not 1 <= dense_retrieval_top_k <= MAX_RAG_TOP_K:
        raise RAGConfigurationError(
            f"DENSE_RETRIEVAL_TOP_K must be between 1 and {MAX_RAG_TOP_K}."
        )
    if not 1 <= sparse_retrieval_top_k <= MAX_RAG_TOP_K:
        raise RAGConfigurationError(
            f"SPARSE_RETRIEVAL_TOP_K must be between 1 and {MAX_RAG_TOP_K}."
        )
    if not 1 <= retrieval_child_top_k <= MAX_RAG_TOP_K:
        raise RAGConfigurationError(
            f"RETRIEVAL_CHILD_TOP_K must be between 1 and {MAX_RAG_TOP_K}."
        )
    if not 1 <= rerank_candidate_top_k <= MAX_RAG_TOP_K:
        raise RAGConfigurationError(
            f"RERANK_CANDIDATE_TOP_K must be between 1 and {MAX_RAG_TOP_K}."
        )
    if not 1 <= rerank_parent_top_k <= MAX_RAG_TOP_K:
        raise RAGConfigurationError(
            f"RERANK_PARENT_TOP_K must be between 1 and {MAX_RAG_TOP_K}."
        )
    if not 0 <= rerank_min_score <= 1:
        raise RAGConfigurationError("RERANK_MIN_SCORE must be between 0 and 1.")

    return RAGSettings(
        qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333").strip(),
        qdrant_collection=os.getenv(
            "QDRANT_COLLECTION", "enterprise_knowledge"
        ).strip(),
        parent_chunk_size=parent_chunk_size,
        child_chunk_size=child_chunk_size,
        child_chunk_overlap=child_chunk_overlap,
        dense_retrieval_top_k=dense_retrieval_top_k,
        sparse_retrieval_top_k=sparse_retrieval_top_k,
        retrieval_child_top_k=retrieval_child_top_k,
        rerank_candidate_top_k=rerank_candidate_top_k,
        rerank_parent_top_k=rerank_parent_top_k,
        rerank_min_score=rerank_min_score,
        rerank_model=os.getenv("RERANK_MODEL", DEFAULT_RERANK_MODEL).strip(),
        embedding_model=os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3").strip(),
        embedding_base_url=os.getenv(
            "EMBEDDING_BASE_URL", "https://api.siliconflow.cn/v1"
        ).strip(),
        embedding_api_key=embedding_api_key,
    )
