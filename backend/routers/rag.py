"""
backend/routers/rag.py
Q&A endpoint — hybrid pipeline router.
Routes to direct_llm_service (≤20K tokens) or rag_service (>20K tokens).
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.middleware.auth_middleware import get_current_user
from backend.models.chat import Chat, Message, SenderEnum
from backend.models.document import Document, PipelineEnum, ProcessingStatusEnum
from backend.models.user import User
from backend.schemas.chat import AskRequest
from backend.services.direct_llm_service import generate_answer_direct
from backend.services.rag_service import generate_answer_rag

logger = logging.getLogger(__name__)
router = APIRouter(tags=["RAG / Q&A"])


@router.post("/chats/{chat_id}/ask")
async def ask(
    chat_id: str,
    body: AskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream an answer to the user's question.

    Routing logic:
    - Determine which document is active for the chat.
    - If pipeline_used == 'direct': pass full document text.
    - If pipeline_used == 'rag':    search Qdrant for relevant chunks.

    Returns a StreamingResponse with SSE-formatted events.
    """
    # ── Validate chat ownership ──────────────────────────────────────
    chat_result = await db.execute(
        select(Chat).where(Chat.chat_id == chat_id, Chat.user_id == current_user.user_id)
    )
    chat = chat_result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found.")

    # ── Resolve active document ──────────────────────────────────────
    doc_id = body.document_id
    doc_query = select(Document).where(
        Document.user_id == current_user.user_id,
        Document.processing_status == ProcessingStatusEnum.ready,
    )
    if doc_id:
        doc_query = doc_query.where(Document.document_id == doc_id)
    else:
        doc_query = doc_query.where(Document.chat_id == chat_id)

    doc_query = doc_query.order_by(Document.upload_time.desc()).limit(1)
    doc_result = await db.execute(doc_query)
    doc = doc_result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=400,
            detail="No processed document found for this chat. Please upload a PDF first.",
        )

    # ── Build chat history ───────────────────────────────────────────
    msg_result = await db.execute(
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.timestamp.desc())
        .limit(20)
    )
    recent_messages = list(reversed(msg_result.scalars().all()))
    chat_history = [
        {"role": m.sender.value, "content": m.message}
        for m in recent_messages
    ]

    # ── Save user message (non-blocking) ────────────────────────────
    user_msg = Message(
        chat_id=chat_id,
        sender=SenderEnum.user,
        message=body.question,
    )
    db.add(user_msg)
    # Update chat title from first question if still default
    if chat.title == "New Chat":
        chat.title = body.question[:60] + ("…" if len(body.question) > 60 else "")
    await db.flush()

    # ── Stream answer ────────────────────────────────────────────────
    async def event_stream():
        full_answer = []
        pipeline = doc.pipeline_used.value

        # Signal pipeline info as first SSE event
        yield f"data: {json.dumps({'type': 'meta', 'pipeline': pipeline, 'doc_name': doc.filename})}\n\n"

        try:
            if pipeline == "direct":
                # Retrieve stored full text from first chunk
                from backend.models.document import DocumentChunk
                chunk_result = await db.execute(
                    select(DocumentChunk)
                    .where(DocumentChunk.document_id == doc.document_id)
                    .order_by(DocumentChunk.chunk_index)
                )
                db_chunks = chunk_result.scalars().all()
                full_text = "\n\n".join(c.chunk_text for c in db_chunks)

                async for token in generate_answer_direct(full_text, body.question, chat_history):
                    full_answer.append(token)
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            else:
                # RAG pipeline
                async for token in generate_answer_rag(
                    doc.document_id, current_user.user_id, body.question, chat_history
                ):
                    full_answer.append(token)
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

        except Exception as exc:
            logger.error("Streaming error in /ask: %s", exc)
            error_msg = f"⚠️ Error generating response: {exc}"
            yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
            full_answer.append(error_msg)

        # Save assistant answer to DB
        assistant_answer = "".join(full_answer)
        if assistant_answer:
            assistant_msg = Message(
                chat_id=chat_id,
                sender=SenderEnum.assistant,
                message=assistant_answer,
            )
            db.add(assistant_msg)
            await db.flush()

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
