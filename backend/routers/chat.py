"""
backend/routers/chat.py
Chat and message management endpoints.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete

from backend.database import get_db
from backend.models.user import User
from backend.models.chat import Chat, Message
from backend.models.document import Document
from backend.middleware.auth_middleware import get_current_user
from backend.schemas.chat import ChatCreate, ChatRename, ChatSummary, ChatDetail, MessageOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chats", tags=["Chats"])


def _assert_owns_chat(chat: Chat | None, user: User) -> Chat:
    """Raise 404 if chat doesn't exist or 403 if user doesn't own it."""
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found.")
    if chat.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    return chat


@router.post("", response_model=ChatDetail, status_code=status.HTTP_201_CREATED)
async def create_chat(
    body: ChatCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new empty chat for the authenticated user."""
    chat = Chat(user_id=current_user.user_id, title=body.title)
    db.add(chat)
    await db.flush()
    return ChatDetail(
        chat_id=chat.chat_id,
        title=chat.title,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        messages=[],
    )


@router.get("", response_model=list[ChatSummary])
async def list_chats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all chats for the authenticated user, newest first."""
    result = await db.execute(
        select(Chat)
        .where(Chat.user_id == current_user.user_id)
        .order_by(Chat.updated_at.desc())
    )
    chats = result.scalars().all()

    summaries = []
    for chat in chats:
        # Count messages
        count_result = await db.execute(
            select(func.count()).where(Message.chat_id == chat.chat_id)
        )
        msg_count = count_result.scalar() or 0

        # Get active document name
        doc_result = await db.execute(
            select(Document.filename)
            .where(Document.chat_id == chat.chat_id)
            .order_by(Document.upload_time.desc())
            .limit(1)
        )
        doc_name = doc_result.scalar_one_or_none()

        summaries.append(ChatSummary(
            chat_id=chat.chat_id,
            title=chat.title,
            message_count=msg_count,
            last_updated=chat.updated_at,
            document_name=doc_name,
        ))
    return summaries


@router.get("/{chat_id}", response_model=ChatDetail)
async def get_chat(
    chat_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a chat with all its messages."""
    result = await db.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat = _assert_owns_chat(result.scalar_one_or_none(), current_user)

    msg_result = await db.execute(
        select(Message).where(Message.chat_id == chat_id).order_by(Message.timestamp)
    )
    messages = msg_result.scalars().all()

    # Get active document info
    doc_result = await db.execute(
        select(Document)
        .where(Document.chat_id == chat_id)
        .order_by(Document.upload_time.desc())
        .limit(1)
    )
    doc = doc_result.scalar_one_or_none()

    return ChatDetail(
        chat_id=chat.chat_id,
        title=chat.title,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        messages=[MessageOut.model_validate(m) for m in messages],
        document_id=doc.document_id if doc else None,
        document_name=doc.filename if doc else None,
        pipeline_used=doc.pipeline_used.value if doc else None,
    )


@router.patch("/{chat_id}", response_model=ChatDetail)
async def rename_chat(
    chat_id: str,
    body: ChatRename,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rename a chat."""
    result = await db.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat = _assert_owns_chat(result.scalar_one_or_none(), current_user)
    chat.title = body.title
    await db.flush()
    return ChatDetail(
        chat_id=chat.chat_id,
        title=chat.title,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        messages=[],
    )


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    chat_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a chat and all its messages (cascade)."""
    result = await db.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat = _assert_owns_chat(result.scalar_one_or_none(), current_user)
    await db.delete(chat)
    logger.info("Deleted chat %s for user %s.", chat_id, current_user.user_id)
    return None
