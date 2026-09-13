import argparse
import asyncio
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import RAGConfigurationError
from app.core.config import MAX_RAG_TOP_K
from app.rag.retrieval_service import retrieve
from app.rag.vectorstore import KnowledgeBaseNotFoundError, KnowledgeBaseUnavailableError


def positive_top_k(value: str) -> int:
    top_k = int(value)
    if not 1 <= top_k <= MAX_RAG_TOP_K:
        raise argparse.ArgumentTypeError(
            f"k must be between 1 and {MAX_RAG_TOP_K}"
        )
    return top_k


async def search(query: str, k: int | None) -> int:
    try:
        results = await retrieve(query, k)
    except (KnowledgeBaseNotFoundError, KnowledgeBaseUnavailableError, RAGConfigurationError) as error:
        print(f"ERROR: {error}")
        return 1

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
    parser = argparse.ArgumentParser(description="Search the local enterprise knowledge base.")
    parser.add_argument("query")
    parser.add_argument("-k", type=positive_top_k, default=None)
    args = parser.parse_args()
    return asyncio.run(search(args.query, args.k))


if __name__ == "__main__":
    raise SystemExit(main())
