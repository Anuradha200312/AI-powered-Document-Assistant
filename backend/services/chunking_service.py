"""
backend/services/chunking_service.py
Splits extracted pages into overlapping text chunks with metadata.
"""
import logging
from dataclasses import dataclass
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.config import get_settings
from backend.services.pdf_service import PageContent

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class TextChunk:
    chunk_id: str          # will be assigned after DB insertion
    document_id: str
    page_number: int
    chunk_index: int
    chunk_text: str


def chunk_pages(
    pages: list[PageContent],
    document_id: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[TextChunk]:
    """
    Split page texts into overlapping chunks while preserving page metadata.

    Strategy:
    - Split each page independently to preserve page_number in metadata.
    - Use LangChain RecursiveCharacterTextSplitter for sentence-aware splits.

    Returns a flat list of TextChunk objects with global chunk_index.
    """
    cs = chunk_size or settings.max_chunk_size
    co = chunk_overlap or settings.chunk_overlap

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=cs,
        chunk_overlap=co,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[TextChunk] = []
    global_idx = 0

    for page in pages:
        if not page.text.strip():
            continue
        page_chunks = splitter.split_text(page.text)
        for local_idx, text in enumerate(page_chunks):
            stripped = text.strip()
            if not stripped:
                continue
            chunks.append(
                TextChunk(
                    chunk_id="",           # assigned after DB save
                    document_id=document_id,
                    page_number=page.page_number,
                    chunk_index=global_idx,
                    chunk_text=stripped,
                )
            )
            global_idx += 1

    logger.info(
        "Chunked document %s into %d chunks (chunk_size=%d, overlap=%d).",
        document_id, len(chunks), cs, co,
    )
    return chunks
