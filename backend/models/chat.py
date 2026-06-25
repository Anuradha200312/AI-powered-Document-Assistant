"""
backend/models/chat.py
Chat and Message ORM models.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, func, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from backend.database import Base


class SenderEnum(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class Chat(Base):
    __tablename__ = "chats"

    chat_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New Chat")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="chats")  # noqa: F821
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="chat", cascade="all, delete-orphan", order_by="Message.timestamp"
    )
    documents: Mapped[list["Document"]] = relationship(  # noqa: F821
        "Document", back_populates="chat"
    )

    def __repr__(self) -> str:
        return f"<Chat id={self.chat_id} title={self.title}>"


class Message(Base):
    __tablename__ = "messages"

    message_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    chat_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chats.chat_id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender: Mapped[SenderEnum] = mapped_column(
        Enum(SenderEnum), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationship
    chat: Mapped[Chat] = relationship("Chat", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message id={self.message_id} sender={self.sender}>"
