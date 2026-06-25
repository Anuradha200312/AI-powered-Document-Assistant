"""
backend/schemas/chat.py
Pydantic schemas for Chat and Message endpoints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Chat Schemas ──────────────────────────────────────────────────

class ChatCreate(BaseModel):
    title: str = Field(default="New Chat", max_length=255)


class ChatRename(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class MessageOut(BaseModel):
    message_id: str
    sender: str
    message: str
    timestamp: datetime

    model_config = {"from_attributes": True}


class ChatSummary(BaseModel):
    chat_id: str
    title: str
    message_count: int
    last_updated: datetime
    document_name: Optional[str] = None

    model_config = {"from_attributes": True}


class ChatDetail(BaseModel):
    chat_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] = []
    document_id: Optional[str] = None
    document_name: Optional[str] = None
    pipeline_used: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Ask / Answer ──────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    document_id: Optional[str] = None  # override active document
