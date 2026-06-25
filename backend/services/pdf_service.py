"""
backend/services/pdf_service.py
PDF text extraction, page-aware processing, and token counting.
"""
import io
import logging
from dataclasses import dataclass

import tiktoken
from PyPDF2 import PdfReader

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Use OpenAI cl100k_base tokeniser — close enough for Groq Llama models
_tokenizer = tiktoken.get_encoding("cl100k_base")

TOKEN_THRESHOLD: int = settings.token_threshold


@dataclass
class PageContent:
    page_number: int   # 1-indexed
    text: str


def extract_pages(file_bytes: bytes) -> list[PageContent]:
    """
    Extract text from every page of a PDF, returning a list of
    PageContent objects preserving page order.

    Raises:
        ValueError: if the PDF has no extractable text.
    """
    reader = PdfReader(io.BytesIO(file_bytes))
    pages: list[PageContent] = []

    for idx, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        # Normalise whitespace while keeping paragraph breaks
        cleaned = "\n".join(line.strip() for line in raw.splitlines() if line.strip())
        if cleaned:
            pages.append(PageContent(page_number=idx, text=cleaned))

    if not pages:
        raise ValueError(
            "This PDF contains no extractable text. "
            "It may be a scanned image — OCR is not supported."
        )

    return pages


def pages_to_full_text(pages: list[PageContent]) -> str:
    """Concatenate all page texts with newlines."""
    return "\n\n".join(p.text for p in pages)


def count_tokens(text: str) -> int:
    """Count tokens in text using the cl100k_base tokenizer."""
    try:
        return len(_tokenizer.encode(text, disallowed_special=()))
    except Exception as exc:
        logger.warning("Token counting fell back to word estimate: %s", exc)
        return len(text.split())


def route_pipeline(token_count: int) -> str:
    """
    Determine which pipeline to use based on token count.
    Returns 'direct' or 'rag'.
    """
    return "rag" if token_count > TOKEN_THRESHOLD else "direct"
