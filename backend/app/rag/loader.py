import hashlib
import re
from io import BytesIO
from pathlib import Path
from uuid import UUID

from langchain_core.documents import Document
from pypdf import PdfReader


SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md"}

_ARTICLE_PREFIX = re.compile(r"^(第[一二三四五六七八九十百千万零〇0-9]+条)(.*)$")
_SECTION_PREFIX = re.compile(r"^(第[一二三四五六七八九十百千万零〇0-9]+[编章节])(.*)$")
_STRUCTURAL_HEADING = re.compile(r"^(目录|附则)$")
_LIST_ITEM = re.compile(r"^（[一二三四五六七八九十]+）")


def get_file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get_document_id(file_hash: str) -> str:
    return str(UUID(file_hash[:32]))


def list_document_paths(documents_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in documents_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )


def _remove_extraction_spaces(line: str) -> str:
    line = re.sub(
        r"(?<=[\u3400-\u4dbf\u4e00-\u9fff0-9]) +(?=[\u3400-\u4dbf\u4e00-\u9fff0-9，。；：、？！）》」』）])",
        "",
        line,
    )
    line = re.sub(r"(?<=[（《“「『]) +", "", line)
    return re.sub(r" +(?=[）》」』）])", "", line)


def _normalize_pdf_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\u3000", " ")
    text = re.sub(
        r"(?m)^\s*[—-]\s*\n\s*\d+\s*\n\s*[—-]\s*$",
        "",
        text,
    )
    text = re.sub(r"(?m)^\s*附\s*\n\s*则\s*$", "附则", text)

    lines = [
        _remove_extraction_spaces(line).strip()
        for line in text.splitlines()
    ]
    lines = [line for line in lines if line]

    normalized_lines: list[str] = []
    previous_was_structure = False
    for line in lines:
        article_match = _ARTICLE_PREFIX.match(line)
        section_match = _SECTION_PREFIX.match(line)
        if article_match:
            suffix = article_match.group(2)
            normalized_lines.append(
                f"{article_match.group(1)} {suffix}" if suffix else f"{article_match.group(1)} "
            )
            previous_was_structure = True
        elif section_match:
            suffix = section_match.group(2)
            normalized_lines.append(
                f"{section_match.group(1)} {suffix}" if suffix else f"{section_match.group(1)} "
            )
            previous_was_structure = True
        elif _STRUCTURAL_HEADING.match(line) or _LIST_ITEM.match(line):
            normalized_lines.append(line)
            previous_was_structure = False
        elif not normalized_lines:
            normalized_lines.append(line)
        elif previous_was_structure:
            normalized_lines[-1] += line
            previous_was_structure = False
        else:
            normalized_lines[-1] += line

    normalized_text = "\n".join(normalized_lines).strip()
    return re.sub(
        r"([：；])（(?=[一二三四五六七八九十]+）)",
        r"\1\n（",
        normalized_text,
    )


def load_document(path: Path) -> list[Document]:
    file_bytes = path.read_bytes()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    base_metadata = {
        "file_hash": file_hash,
        "filename": path.name,
        "source": str(path.resolve()),
        "parser": "pypdf" if path.suffix.lower() == ".pdf" else "text",
    }

    if path.suffix.lower() == ".pdf":
        reader = PdfReader(BytesIO(file_bytes))
        return [
            Document(
                page_content=_normalize_pdf_text(page.extract_text() or ""),
                metadata={**base_metadata, "page": page_number},
            )
            for page_number, page in enumerate(reader.pages, start=1)
        ]

    return [
        Document(
            page_content=file_bytes.decode("utf-8-sig"),
            metadata={**base_metadata, "page": None},
        )
    ]
