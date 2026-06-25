"""
backend/routers/documents.py
PDF upload, async processing, status polling, and deletion.
"""
import asyncio
import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.config import get_settings
from backend.database import get_db
from backend.middleware.auth_middleware import get_current_user
from backend.models.document import Document, DocumentChunk, PipelineEnum, ProcessingStatusEnum
from backend.models.user import User
from backend.schemas.document import DocumentOut, DocumentStatusOut
from backend.services import (
    pdf_service,
    chunking_service,
    embedding_service,
    qdrant_service,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents"])
settings = get_settings()

# Thread pool for CPU-bound PDF/embedding work
_executor = ThreadPoolExecutor(max_workers=4)


def _process_document_sync(
    document_id: str,
    file_bytes: bytes,
    filename: str,
    user_id: str,
    chat_id: str | None,
    db_url: str,
) -> None:
    """
    CPU-bound work executed in a thread pool:
    1. Extract text + count tokens.
    2. Route to direct or RAG pipeline.
    3. For RAG: chunk → embed → upsert to Qdrant.

    Updates document record status directly via a synchronous DB connection.
    """
    import asyncio
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, Session

    # Sync engine for the worker thread
    sync_url = db_url.replace("+asyncpg", "+psycopg2").replace(
        "postgresql+psycopg2", "postgresql"
    )
    engine = create_engine(sync_url, pool_pre_ping=True)
    SyncSession = sessionmaker(bind=engine, expire_on_commit=False)

    def _update_status(session: Session, status: ProcessingStatusEnum, **kwargs):
        doc = session.get(Document, document_id)
        if doc:
            doc.processing_status = status
            for k, v in kwargs.items():
                setattr(doc, k, v)
            session.commit()

    with SyncSession() as session:
        try:
            _update_status(session, ProcessingStatusEnum.processing)

            # Extract text
            pages = pdf_service.extract_pages(file_bytes)
            full_text = pdf_service.pages_to_full_text(pages)
            token_count = pdf_service.count_tokens(full_text)
            pipeline = pdf_service.route_pipeline(token_count)

            logger.info(
                "Document %s: %d tokens → pipeline=%s", document_id, token_count, pipeline
            )

            doc = session.get(Document, document_id)
            if doc:
                doc.token_count = token_count
                doc.pipeline_used = PipelineEnum(pipeline)
                session.commit()

            if pipeline == "rag":
                # Check for duplicate indexing
                collection_name = qdrant_service.get_collection_name(user_id)
                if not qdrant_service.document_already_indexed(collection_name, document_id):
                    chunks = chunking_service.chunk_pages(pages, document_id)
                    texts = [c.chunk_text for c in chunks]
                    embeddings = embedding_service.get_embeddings(texts)

                    qdrant_service.upsert_chunks(
                        collection_name=collection_name,
                        chunks=chunks,
                        embeddings=embeddings,
                        user_id=user_id,
                        chat_id=chat_id,
                    )

                    # Store chunks in PostgreSQL too
                    db_chunks = [
                        DocumentChunk(
                            document_id=document_id,
                            page_number=c.page_number,
                            chunk_index=c.chunk_index,
                            chunk_text=c.chunk_text,
                        )
                        for c in chunks
                    ]
                    session.add_all(db_chunks)
                    session.commit()

                _update_status(
                    session, ProcessingStatusEnum.ready,
                    qdrant_collection=collection_name,
                )
            else:
                # Direct pipeline — store full text as a single chunk for reference
                chunk = DocumentChunk(
                    document_id=document_id,
                    page_number=0,
                    chunk_index=0,
                    chunk_text=full_text[:10000],  # store truncated for preview
                )
                session.add(chunk)
                _update_status(session, ProcessingStatusEnum.ready)

        except Exception as exc:
            logger.error("Document processing failed [%s]: %s", document_id, exc)
            _update_status(
                session, ProcessingStatusEnum.error,
                error_message=str(exc)[:500],
            )
        finally:
            engine.dispose()


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    chat_id: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a PDF. Processing (tokenisation, chunking, embedding) happens
    asynchronously in the background. Poll /documents/{id}/status for progress.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Validate chat ownership if chat_id provided
    if chat_id:
        from backend.models.chat import Chat
        chat_result = await db.execute(
            select(Chat).where(Chat.chat_id == chat_id, Chat.user_id == current_user.user_id)
        )
        if not chat_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Chat not found.")

    # Save file to disk
    os.makedirs(settings.upload_dir, exist_ok=True)
    safe_name = f"{uuid.uuid4()}_{file.filename}"
    filepath = os.path.join(settings.upload_dir, safe_name)
    with open(filepath, "wb") as f:
        f.write(file_bytes)

    # Create DB record
    doc = Document(
        user_id=current_user.user_id,
        chat_id=chat_id,
        filename=file.filename,
        processing_status=ProcessingStatusEnum.pending,
        pipeline_used=PipelineEnum.pending,
    )
    db.add(doc)
    await db.flush()

    # Launch background processing
    loop = asyncio.get_event_loop()
    loop.run_in_executor(
        _executor,
        _process_document_sync,
        doc.document_id,
        file_bytes,
        file.filename,
        current_user.user_id,
        chat_id,
        settings.database_url,
    )

    logger.info("Upload queued: doc=%s user=%s", doc.document_id, current_user.user_id)
    return doc


@router.get("/{document_id}/status", response_model=DocumentStatusOut)
async def get_document_status(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Poll document processing status."""
    result = await db.execute(
        select(Document).where(
            Document.document_id == document_id,
            Document.user_id == current_user.user_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all documents uploaded by the authenticated user."""
    result = await db.execute(
        select(Document)
        .where(Document.user_id == current_user.user_id)
        .order_by(Document.upload_time.desc())
    )
    return result.scalars().all()


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and its Qdrant vectors."""
    result = await db.execute(
        select(Document).where(
            Document.document_id == document_id,
            Document.user_id == current_user.user_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Remove from Qdrant if RAG-indexed
    if doc.qdrant_collection:
        qdrant_service.delete_document_vectors(doc.qdrant_collection, document_id)

    await db.delete(doc)
    logger.info("Deleted document %s for user %s.", document_id, current_user.user_id)
    return None
