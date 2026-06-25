"""
backend/services/qdrant_service.py
Qdrant vector store operations: create collection, upsert, search, delete.
"""
import logging
from functools import lru_cache
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from backend.config import get_settings
from backend.services.chunking_service import TextChunk

logger = logging.getLogger(__name__)
settings = get_settings()

COLLECTION_PREFIX = "docmind"


@lru_cache(maxsize=1)
def _get_client() -> QdrantClient:
    """Return a cached Qdrant client instance."""
    if settings.qdrant_url:
        # Qdrant Cloud
        client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
        logger.info("Connected to Qdrant Cloud: %s", settings.qdrant_url)
    else:
        # Local Qdrant
        client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        logger.info("Connected to local Qdrant at %s:%d", settings.qdrant_host, settings.qdrant_port)
    return client


def get_collection_name(user_id: str) -> str:
    """Each user gets their own Qdrant collection."""
    return f"{COLLECTION_PREFIX}_user_{user_id[:8]}"


def ensure_collection(collection_name: str) -> None:
    """Create the collection if it doesn't exist."""
    client = _get_client()
    existing = [c.name for c in client.get_collections().collections]
    if collection_name not in existing:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=qmodels.VectorParams(
                size=settings.embedding_dimension,
                distance=qmodels.Distance.COSINE,
            ),
        )
        logger.info("Created Qdrant collection: %s", collection_name)


def document_already_indexed(collection_name: str, document_id: str) -> bool:
    """Check if a document has already been indexed (duplicate detection)."""
    client = _get_client()
    try:
        results = client.scroll(
            collection_name=collection_name,
            scroll_filter=qmodels.Filter(
                must=[qmodels.FieldCondition(
                    key="document_id",
                    match=qmodels.MatchValue(value=document_id),
                )]
            ),
            limit=1,
            with_payload=False,
            with_vectors=False,
        )
        points, _ = results
        return len(points) > 0
    except Exception:
        return False


def upsert_chunks(
    collection_name: str,
    chunks: list[TextChunk],
    embeddings: list[list[float]],
    user_id: str,
    chat_id: str | None,
) -> None:
    """
    Store text chunks with their embeddings and metadata in Qdrant.
    Uses upsert to avoid duplicates on retry.
    """
    client = _get_client()
    ensure_collection(collection_name)

    points = [
        qmodels.PointStruct(
            id=abs(hash(f"{chunk.document_id}_{chunk.chunk_index}")) % (2**63),
            vector=embedding,
            payload={
                "chunk_text": chunk.chunk_text,
                "document_id": chunk.document_id,
                "user_id": user_id,
                "chat_id": chat_id or "",
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
            },
        )
        for chunk, embedding in zip(chunks, embeddings)
    ]

    client.upsert(collection_name=collection_name, points=points, wait=True)
    logger.info("Upserted %d points to collection %s.", len(points), collection_name)


def search_similar_chunks(
    collection_name: str,
    query_embedding: list[float],
    document_id: str | None = None,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """
    Search for the most similar chunks in Qdrant.

    Args:
        collection_name: Target collection.
        query_embedding: Embedded user question.
        document_id:     If set, filter results to this document only.
        top_k:          Number of results to return.

    Returns:
        List of dicts with keys: chunk_text, page_number, chunk_index, score.
    """
    client = _get_client()
    k = top_k or settings.rag_top_k

    search_filter = None
    if document_id:
        search_filter = qmodels.Filter(
            must=[qmodels.FieldCondition(
                key="document_id",
                match=qmodels.MatchValue(value=document_id),
            )]
        )

    results = client.search(
        collection_name=collection_name,
        query_vector=query_embedding,
        query_filter=search_filter,
        limit=k,
        with_payload=True,
    )

    return [
        {
            "chunk_text": r.payload.get("chunk_text", ""),
            "page_number": r.payload.get("page_number", 0),
            "chunk_index": r.payload.get("chunk_index", 0),
            "score": r.score,
        }
        for r in results
        if r.payload
    ]


def delete_document_vectors(collection_name: str, document_id: str) -> int:
    """Delete all Qdrant vectors belonging to a document. Returns deleted count."""
    client = _get_client()
    try:
        client.delete(
            collection_name=collection_name,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[qmodels.FieldCondition(
                        key="document_id",
                        match=qmodels.MatchValue(value=document_id),
                    )]
                )
            ),
        )
        logger.info("Deleted vectors for document %s from %s.", document_id, collection_name)
        return 1
    except Exception as exc:
        logger.error("Failed to delete Qdrant vectors for %s: %s", document_id, exc)
        return 0
