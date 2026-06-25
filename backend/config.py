"""
backend/config.py
Centralised application settings loaded from .env
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Groq ─────────────────────────────────────────────────────
    groq_api_key: str = ""

    # ── PostgreSQL ────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/docmind"

    # ── JWT ───────────────────────────────────────────────────────
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # ── Qdrant ────────────────────────────────────────────────────
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_url: str = ""       # override for Qdrant Cloud
    qdrant_api_key: str = ""   # for Qdrant Cloud

    # ── App ───────────────────────────────────────────────────────
    upload_dir: str = "uploads"
    token_threshold: int = 20_000
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    max_chunk_size: int = 800
    chunk_overlap: int = 150
    rag_top_k: int = 5
    max_history_turns: int = 10


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
