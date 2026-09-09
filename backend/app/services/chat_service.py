import asyncio
import json
from collections.abc import AsyncIterator
from time import monotonic
from uuid import uuid4

from fastapi import Request
from openai import AsyncOpenAI, DefaultAsyncHttpxClient, OpenAIError

from app.core.config import LongCatConfigurationError, LongCatSettings, get_longcat_settings
from app.schemas.chat import ChatRequest
from app.services.thread_service import (
    ThreadNotFoundError,
    add_message,
    create_thread_with_message,
    get_thread,
    list_messages,
    update_thread_title,
)


def _sse(data: dict[str, object]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _title_from_message(message: str) -> str:
    return " ".join(message.split())[:80] or "New chat"


def get_longcat_client(settings: LongCatSettings) -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.api_key,
        base_url=settings.base_url,
        http_client=DefaultAsyncHttpxClient(trust_env=False),
    )


async def stream_chat_response(
    request: ChatRequest,
    http_request: Request,
) -> AsyncIterator[str]:
    try:
        title = _title_from_message(request.message)
        if request.thread_id:
            thread = get_thread(request.thread_id)
            if thread.title == "New chat":
                thread = update_thread_title(thread.id, title)
            add_message(thread.id, "user", request.message)
        else:
            thread = create_thread_with_message(title, request.message)

        thread = get_thread(thread.id)
        history = list_messages(thread.id)
        assistant_message_id = str(uuid4())
        yield _sse(
            {
                "type": "start",
                "thread_id": thread.id,
                "assistant_message_id": assistant_message_id,
                "thread": thread.model_dump(mode="json"),
            }
        )

        settings = get_longcat_settings()
        client = get_longcat_client(settings)
        thinking_started_at = monotonic()
        thinking_duration_ms: int | None = None
        stream = None
        try:
            stream = await client.chat.completions.create(
                model=settings.model,
                messages=[
                    {"role": message.role, "content": message.content}
                    for message in history
                ],
                max_tokens=1024,
                temperature=0.7,
                extra_body={"thinking": {"type": "enabled"}},
                stream=True,
            )
            reasoning_parts: list[str] = []
            content_parts: list[str] = []

            async for chunk in stream:
                if await http_request.is_disconnected():
                    return
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                reasoning_content = delta.model_extra.get("reasoning_content", "")
                if reasoning_content:
                    reasoning_parts.append(reasoning_content)
                    yield _sse(
                        {
                            "type": "reasoning_delta",
                            "content": reasoning_content,
                        }
                    )

                content = delta.content
                if not content:
                    continue

                if thinking_duration_ms is None:
                    thinking_duration_ms = int((monotonic() - thinking_started_at) * 1000)
                    yield _sse(
                        {
                            "type": "thinking_complete",
                            "thinking_duration_ms": thinking_duration_ms,
                        }
                    )

                content_parts.append(content)
                yield _sse({"type": "delta", "content": content})
        finally:
            if stream is not None:
                await stream.close()
            await client.close()

        content = "".join(content_parts)
        reasoning_content = "".join(reasoning_parts)
        if thinking_duration_ms is None:
            thinking_duration_ms = int((monotonic() - thinking_started_at) * 1000)
        add_message(
            thread.id,
            "assistant",
            content,
            reasoning_content=reasoning_content,
            thinking_duration_ms=thinking_duration_ms,
            message_id=assistant_message_id,
        )
        latest_thread = get_thread(thread.id)
        yield _sse(
            {
                "type": "done",
                "thread_id": thread.id,
                "message_id": assistant_message_id,
                "thread": latest_thread.model_dump(mode="json"),
                "thinking_duration_ms": thinking_duration_ms,
            }
        )
    except asyncio.CancelledError:
        raise
    except ThreadNotFoundError:
        yield _sse(
            {
                "type": "error",
                "code": "THREAD_NOT_FOUND",
                "message": "会话不存在。",
            }
        )
    except LongCatConfigurationError:
        yield _sse(
            {
                "type": "error",
                "code": "CONFIGURATION_ERROR",
                "message": "模型服务尚未配置。",
            }
        )
    except OpenAIError:
        yield _sse(
            {
                "type": "error",
                "code": "MODEL_ERROR",
                "message": "模型调用失败。",
            }
        )
