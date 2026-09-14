"""对外暴露健康检查、聊天、知识库检索和会话管理接口。"""

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from app.core.config import (
    RAGConfigurationError,
    get_configured_model,
    get_context_window_tokens,
)
from app.schemas.chat import ChatRequest
from app.schemas.health import HealthResponse
from app.schemas.model import ModelResponse
from app.rag.retrieval_service import retrieve
from app.rag.schemas import RagSearchRequest, RagSearchResponse
from app.rag.vectorstore import KnowledgeBaseNotFoundError, KnowledgeBaseUnavailableError
from app.services.chat_service import stream_chat_response
from app.schemas.thread import MessageResponse, ThreadResponse
from app.services.thread_service import (
    ThreadNotFoundError,
    delete_thread,
    list_messages,
    list_threads,
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """返回服务进程可用状态。"""
    return HealthResponse(status="ok")


@router.post("/api/chat")
async def chat(request: ChatRequest, http_request: Request) -> StreamingResponse:
    """以 SSE 形式转发聊天生成过程，保持连接可及时推送增量事件。"""
    return StreamingResponse(
        stream_chat_response(request, http_request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/rag/search", response_model=RagSearchResponse)
async def search_knowledge_base(request: RagSearchRequest) -> RagSearchResponse:
    """执行独立的知识库检索，统一转换配置和基础设施错误。"""
    try:
        results = await retrieve(request.query, request.k)
    except RAGConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except KnowledgeBaseNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except KnowledgeBaseUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    return RagSearchResponse(query=request.query, results=results)


@router.get("/api/threads", response_model=list[ThreadResponse])
async def get_threads() -> list[ThreadResponse]:
    """按最近更新时间返回会话列表。"""
    return await list_threads()


@router.get("/api/models", response_model=list[ModelResponse])
async def get_models() -> list[ModelResponse]:
    """返回当前后端实际启用的模型及其思考档位。"""
    model = get_configured_model()
    label = "GLM-5.3 Flash" if model == "glm-5.3-flash" else model
    return [
        ModelResponse(
            id=model,
            label=label,
            context_window_tokens=get_context_window_tokens(),
            thinking_levels=["off", "low", "medium", "high", "xhigh"],
        )
    ]


@router.delete("/api/threads/{thread_id}", status_code=204)
async def remove_thread(thread_id: str) -> Response:
    """删除会话及其级联消息。"""
    try:
        await delete_thread(thread_id)
    except ThreadNotFoundError as error:
        raise HTTPException(status_code=404, detail="Thread not found.") from error
    return Response(status_code=204)


@router.get("/api/threads/{thread_id}/messages", response_model=list[MessageResponse])
async def get_thread_messages(thread_id: str) -> list[MessageResponse]:
    """返回指定会话的历史消息。"""
    try:
        return await list_messages(thread_id)
    except ThreadNotFoundError as error:
        raise HTTPException(status_code=404, detail="Thread not found.") from error
