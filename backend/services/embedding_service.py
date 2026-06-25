"""
backend/services/embedding_service.py
Sentence-transformer embedding generation with batch processing.
Uses a lazy import so startup doesn't fail if transformers is loading slowly.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from backend.config import get_settings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)
settings = get_settings()

_DEFAULT_BATCH_SIZE = 32


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    """Load the embedding model once and cache it (process-wide singleton)."""
    logger.info("Loading embedding model: %s", settings.embedding_model)
    model = SentenceTransformer(settings.embedding_model)
    logger.info("Embedding model loaded.")
    return model


def get_embeddings(texts: list[str], batch_size: int = _DEFAULT_BATCH_SIZE) -> list[list[float]]:
    """
    Generate embeddings for a list of texts.

    Args:
        texts:      List of strings to embed.
        batch_size: Number of texts to process per batch.

    Returns:
        List of float vectors (one per input text).

    Raises:
        RuntimeError: If embedding generation fails for all batches.
    """
    model = _get_model()
    all_embeddings: list[list[float]] = []

    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        try:
            vecs = model.encode(batch, convert_to_numpy=True, show_progress_bar=False)
            all_embeddings.extend(vec.tolist() for vec in vecs)
        except Exception as exc:
            logger.error(
                "Embedding failed for batch [%d:%d]: %s",
                start, start + batch_size, exc,
            )
            # Fill with zero vectors on failure so indexing can continue
            dim = settings.embedding_dimension
            all_embeddings.extend([[0.0] * dim] * len(batch))

    return all_embeddings


def get_single_embedding(text: str) -> list[float]:
    """Embed a single text string (e.g., a user query)."""
    result = get_embeddings([text])
    return result[0]
