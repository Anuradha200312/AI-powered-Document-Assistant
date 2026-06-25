"""
backend/services/rag_service.py
Pipeline for large documents (>20K tokens).
Retrieves relevant chunks from Qdrant and sends them to Groq.
"""
import logging
from typing import AsyncGenerator

from groq import AsyncGroq

from backend.config import get_settings
from backend.services.embedding_service import get_single_embedding
from backend.services.qdrant_service import search_similar_chunks, get_collection_name

logger = logging.getLogger(__name__)
settings = get_settings()

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


RAG_SYSTEM_PROMPT = """You are an intelligent document assistant.

You are provided with relevant context retrieved from a large document.

Instructions:
- Answer ONLY using the provided context.
- Preserve original formatting wherever possible.
- Maintain headings, bullet points, tables, and numbering.
- Do not invent information not present in the context.
- If the answer is not present in the provided context, clearly state:
  "I could not find that information in the sections retrieved from the document."
- Produce a clean, professional, and well-formatted response.
- When possible, cite the page number (e.g., "According to page 3...").
"""


async def generate_answer_rag(
    document_id: str,
    user_id: str,
    question: str,
    chat_history: list[dict],
) -> AsyncGenerator[str, None]:
    """
    Stream an answer using the RAG pipeline:
    1. Embed the question.
    2. Search Qdrant for relevant chunks (filtered by document_id).
    3. Build context from retrieved chunks.
    4. Stream Groq LLM response.

    Args:
        document_id:  The active document's UUID.
        user_id:      The authenticated user's UUID.
        question:     The user's question.
        chat_history: Recent messages for conversational context.

    Yields:
        String tokens of the streaming response.
    """
    collection_name = get_collection_name(user_id)

    # Step 1: Embed query
    try:
        query_embedding = get_single_embedding(question)
    except Exception as exc:
        logger.error("Query embedding failed: %s", exc)
        yield "⚠️ Failed to process your question. Please try again."
        return

    # Step 2: Search Qdrant
    try:
        retrieved = search_similar_chunks(
            collection_name=collection_name,
            query_embedding=query_embedding,
            document_id=document_id,
            top_k=settings.rag_top_k,
        )
    except Exception as exc:
        logger.error("Qdrant search failed: %s", exc)
        yield "⚠️ Vector search failed. Please ensure Qdrant is running."
        return

    if not retrieved:
        yield (
            "I could not find relevant information in the document for your question. "
            "Please try rephrasing or ask about a different topic."
        )
        return

    # Step 3: Build context string with page citations
    context_parts = []
    for i, chunk in enumerate(retrieved, start=1):
        page_ref = f"[Page {chunk['page_number']}]" if chunk["page_number"] else ""
        context_parts.append(f"--- Chunk {i} {page_ref} ---\n{chunk['chunk_text']}")

    context = "\n\n".join(context_parts)

    # Step 4: Build messages
    max_turns = settings.max_history_turns
    trimmed_history = chat_history[-max_turns * 2:]

    messages = [
        {"role": "system", "content": RAG_SYSTEM_PROMPT},
        *trimmed_history,
        {
            "role": "user",
            "content": (
                f"Context:\n{context}\n\n"
                f"User Question:\n{question}"
            ),
        },
    ]

    # Step 5: Stream response
    try:
        response = await _get_client().chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.3,
            max_tokens=1024,
            stream=True,
        )

        async for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    except Exception as exc:
        logger.error("RAG LLM streaming error: %s", exc)
        yield f"\n\n⚠️ An error occurred while generating the response: {exc}"
