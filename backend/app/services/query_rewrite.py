"""提供 Standard RAG 可选的查询改写步骤。"""

import logging

from openai import AsyncOpenAI, OpenAIError

from app.services.model_params import get_thinking_parameters

logger = logging.getLogger(__name__)

QUERY_REWRITE_SYSTEM_PROMPT = """你负责把用户问题改写成企业知识库检索 query。
结合给出的历史对话，补全省略的主语、对象和上下文，把指代词改成明确表述。
保留原问题的意图，不要添加历史对话中没有的事实。
只输出一条适合检索的中文问题，不要输出解释、引号或其他内容。"""


async def rewrite_query(
    client: AsyncOpenAI,
    model: str,
    message: str,
    history: list[dict[str, str]],
) -> str:
    """结合最近对话补全检索 query，失败时保留原始问题。"""
    context = history[-4:]
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": QUERY_REWRITE_SYSTEM_PROMPT},
                *context,
                {"role": "user", "content": message},
            ],
            max_tokens=128,
            temperature=0,
            extra_body=get_thinking_parameters(model),
        )
        rewritten = response.choices[0].message.content or ""
    except OpenAIError:
        logger.warning("Query rewrite failed; using the original query.", exc_info=True)
        return message

    return rewritten.strip() or message
