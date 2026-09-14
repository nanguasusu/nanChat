"""命令行执行一次知识库检索并打印 Parent 结果。"""

import argparse
import asyncio
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.clients import close_clients
from app.core.config import MAX_RAG_TOP_K, RAGConfigurationError
from app.rag.retrieval_service import retrieve
from app.rag.vectorstore import KnowledgeBaseNotFoundError, KnowledgeBaseUnavailableError


def positive_top_k(value: str) -> int:
    """校验命令行的返回数量处于统一的 RAG 上限内。"""
    top_k = int(value)
    if not 1 <= top_k <= MAX_RAG_TOP_K:
        raise argparse.ArgumentTypeError(
            f"k must be between 1 and {MAX_RAG_TOP_K}"
        )
    return top_k


async def search(query: str, k: int | None) -> int:
    """执行检索并以便于人工查看的格式输出来源和片段。"""
    try:
        results = await retrieve(query, k)
    except (KnowledgeBaseNotFoundError, KnowledgeBaseUnavailableError, RAGConfigurationError) as error:
        print(f"ERROR: {error}")
        return 1
    finally:
        await close_clients()

    print(f"Query: {query}\n")
    for index, result in enumerate(results, start=1):
        score = f"{result.score:.4f}"
        if result.page_start is None:
            page = "page n/a"
        elif result.page_start == result.page_end:
            page = f"page {result.page_start}"
        else:
            page = f"pages {result.page_start}-{result.page_end}"
        print(f"#{index} score={score}")
        print(
            f"{result.filename} · {page} · "
            f"parent={result.parent_id} · child_hits={result.hit_count}"
        )
        print(f"\n{result.content}\n")
        print("--------------------------------")
    return 0


def main() -> int:
    """解析命令行参数并启动异步检索。"""
    parser = argparse.ArgumentParser(description="Search the local enterprise knowledge base.")
    parser.add_argument("query")
    parser.add_argument("-k", type=positive_top_k, default=None)
    args = parser.parse_args()
    return asyncio.run(search(args.query, args.k))


if __name__ == "__main__":
    raise SystemExit(main())
