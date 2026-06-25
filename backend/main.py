"""
backend/main.py
FastAPI application entry point.
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import get_settings
from backend.database import create_all_tables
from backend.routers import auth, chat, documents, rag

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables and ensure upload directory on startup."""
    logger.info("Starting DocMind AI backend...")

    # Create all database tables
    try:
        await create_all_tables()
        logger.info("Database tables ready.")
    except Exception as exc:
        logger.error("Failed to create database tables: %s", exc)
        logger.warning(
            "The app will start but database features will not work. "
            "Check your DATABASE_URL in .env"
        )

    # Ensure uploads directory
    os.makedirs(settings.upload_dir, exist_ok=True)

    yield  # App is running

    logger.info("DocMind AI backend shutting down.")


app = FastAPI(
    title="DocMind AI",
    description="Hybrid RAG Document Assistant with multi-user support",
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routers ───────────────────────────────────────────────────
API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(chat.router, prefix=API_PREFIX)
app.include_router(documents.router, prefix=API_PREFIX)
app.include_router(rag.router, prefix=API_PREFIX)

# ── Static Frontend ───────────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIR)), name="frontend_static")

    @app.get("/", response_class=FileResponse)
    async def root():
        """Serve the authentication page."""
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/app", response_class=FileResponse)
    async def serve_app():
        """Serve the main chat application page."""
        return FileResponse(os.path.join(FRONTEND_DIR, "app.html"))
else:
    @app.get("/")
    async def root():
        return {
            "service": "DocMind AI API",
            "version": "2.0.0",
            "docs": "/docs",
            "status": "running",
        }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


# ── Entry point ───────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
