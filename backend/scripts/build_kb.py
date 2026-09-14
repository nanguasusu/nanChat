"""命令行构建或重建本地知识库。"""

import argparse
import asyncio
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.clients import close_clients
from app.core.config import RAGConfigurationError
from app.core.database import init_database
from app.rag.ingestion import ingest_document
from app.rag.loader import list_document_paths
from app.rag.repository import clear_knowledge_base
from app.rag.vectorstore import (
    KnowledgeBaseUnavailableError,
    delete_collection,
)


async def build_knowledge_base(documents_dir: Path, rebuild: bool) -> int:
    """遍历文档目录并逐个入库，单个坏文件不会阻断其他文档。"""
    await init_database()
    paths = list_document_paths(documents_dir)
    print(f"Found {len(paths)} documents")

    if rebuild:
        await delete_collection()
        await clear_knowledge_base()

    successful_documents = 0
    failed_documents = 0
    indexed_chunks = 0

    try:
        for index, path in enumerate(paths, start=1):
            print(f"\n[{index}/{len(paths)}] {path.name}")
            try:
                result = await ingest_document(path)
            except (KnowledgeBaseUnavailableError, RAGConfigurationError) as error:
                print(f"  ERROR: {error}")
                return 1
            except Exception as error:
                failed_documents += 1
                print(f"  ERROR: {error}")
                continue

            successful_documents += 1
            indexed_chunks += result.child_count
            print(f"  parents: {result.parent_count}")
            print(f"  children indexed: {result.child_count}")
    finally:
        await close_clients()

    print("\nDone")
    print(
        f"Documents: {successful_documents} successful / {failed_documents} failed"
    )
    print(f"Chunks indexed: {indexed_chunks}")
    return 0


def main() -> int:
    """解析命令行参数并启动异步构建流程。"""
    parser = argparse.ArgumentParser(description="Build the local enterprise knowledge base.")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Delete the configured Qdrant collection before indexing.",
    )
    args = parser.parse_args()
    documents_dir = PROJECT_ROOT / "knowledge" / "documents"
    return asyncio.run(build_knowledge_base(documents_dir, args.rebuild))


if __name__ == "__main__":
    raise SystemExit(main())
