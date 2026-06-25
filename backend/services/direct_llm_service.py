"""
backend/services/direct_llm_service.py
Pipeline for small documents (≤20K tokens).
Sends the complete document text directly to the Groq LLM.
This preserves the existing streamlit_app.py behaviour.
"""
import logging
from typing import AsyncGenerator

from groq import AsyncGroq

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


SYSTEM_PROMPT = (
    "You are a precise AI document assistant. "
    "Answer questions ONLY based on the document text provided. "
    "If the answer is not in the document, say exactly: "
    "'I don't have that information in this document.' "
    "Do NOT fabricate facts. Be concise, accurate, and well-formatted. "
    "Preserve the document's structure — use headings, bullet points, "
    "tables, and numbering where appropriate."
)


async def generate_answer_direct(
    full_text: str,
    question: str,
    chat_history: list[dict],
) -> AsyncGenerator[str, None]:
    """
    Stream an answer from Groq using the full document text as context.

    Args:
        full_text:    Complete text of the uploaded PDF.
        question:     The user's question.
        chat_history: Recent messages [{"role": ..., "content": ...}, ...]

    Yields:
        String tokens of the streaming response.
    """
    # Keep last N turns to stay within context window
    max_turns = settings.max_history_turns
    trimmed_history = chat_history[-max_turns * 2:]  # pairs of user+assistant

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *trimmed_history,
        {
            "role": "user",
            "content": (
                f"Document Content:\n\n{full_text}\n\n"
                f"Question: {question}"
            ),
        },
    ]

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
        logger.error("Direct LLM streaming error: %s", exc)
        yield f"\n\n⚠️ An error occurred while generating the response: {exc}"
