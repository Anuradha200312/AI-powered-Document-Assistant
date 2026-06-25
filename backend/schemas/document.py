"""
backend/schemas/document.py
Pydantic schemas for Document endpoints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DocumentOut(BaseModel):
    document_id: str
    filename: str
    token_count: int
    upload_time: datetime
    pipeline_used: str
    processing_status: str
    error_message: Optional[str] = None
    chat_id: Optional[str] = None

    model_config = {"from_attributes": True}


class DocumentStatusOut(BaseModel):
    document_id: str
    processing_status: str
    pipeline_used: str
    token_count: int
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}
