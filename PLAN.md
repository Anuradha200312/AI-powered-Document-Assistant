# DocMind AI — Upgraded Architecture Plan

> From MVP → Production-grade Multi-user RAG Document Assistant

---

## Overview

The current app is a single-user, session-only, in-memory document assistant.
This plan upgrades it to a **multi-user, persistent, hybrid RAG pipeline** with
proper chat history, user authentication, and Streamlit UI — all inspired by the
existing `streamlit_app.py` codebase.

---

## Final Project Structure

```
docmind-ai/
├── streamlit_app.py          ← Main entry point (UI only)
├── requirements.txt
├── .env
├── .gitignore
├── README.md
│
├── core/
│   ├── __init__.py
│   ├── auth.py               ← User registration, login, JWT/session
│   ├── database.py           ← PostgreSQL connection (SQLAlchemy)
│   ├── models.py             ← DB models: User, ChatSession, Message
│   └── token_counter.py      ← Count tokens to decide pipeline route
│
├── pipeline/
│   ├── __init__.py
│   ├── router.py             ← Hybrid router: small doc vs large doc
│   ├── small_doc.py          ← Current in-memory pipeline (< 20k tokens)
│   └── rag_pipeline.py       ← New RAG pipeline (> 20k tokens, LangGraph)
│
└── .streamlit/
    ├── config.toml
    └── secrets.toml
```

---

## Phase 1 — User Authentication (PostgreSQL)

### What to build
- Registration and login screen in Streamlit (replace welcome screen)
- Passwords hashed with `bcrypt`
- Session stored in `st.session_state` after login

### PostgreSQL Tables

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Chat sessions (like Claude/ChatGPT sidebar threads)
CREATE TABLE chat_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200),                  -- auto-generated from first question
    document_name VARCHAR(300),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Individual messages per session
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,           -- 'user' or 'assistant'
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Key rules
- User A **never** sees User B's sessions or messages (filter by `user_id`)
- Each session is independent — like separate chats in ChatGPT sidebar
- Session title = first 50 chars of user's first question (auto-generated)

### Files to create
- `core/database.py` — SQLAlchemy engine + session factory
- `core/models.py` — ORM models for all 3 tables
- `core/auth.py` — `register_user()`, `login_user()`, `get_user_sessions()`

---

## Phase 2 — Hybrid Pipeline Router

### Decision logic

```
PDF uploaded
    └──► Count tokens (tiktoken)
         ├── tokens < 20,000  →  Small Doc Pipeline (existing in-memory)
         └── tokens ≥ 20,000  →  RAG Pipeline (Qdrant + LangGraph)
```

### `core/token_counter.py`

```python
import tiktoken

def count_tokens(text: str) -> int:
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))

SMALL_DOC_THRESHOLD = 20_000  # tokens
```

### `pipeline/router.py`

```python
from core.token_counter import count_tokens, SMALL_DOC_THRESHOLD
from pipeline.small_doc import run_small_doc_pipeline
from pipeline.rag_pipeline import run_rag_pipeline

def route_pipeline(text: str, question: str, chat_history: list, session_id: int):
    token_count = count_tokens(text)
    if token_count < SMALL_DOC_THRESHOLD:
        return run_small_doc_pipeline(text, question, chat_history)
    else:
        return run_rag_pipeline(text, question, chat_history, session_id)
```

---

## Phase 3 — Small Doc Pipeline (existing, keep as-is)

**No changes needed.** Already works for PDFs under 20k tokens.

- Extract text with PyPDF2
- Split into chunks with `RecursiveCharacterTextSplitter`
- In-memory cosine similarity search
- Pass top 3 chunks to Groq LLM
- Stream answer back

---

## Phase 4 — RAG Pipeline (LangGraph + LangChain + Qdrant)

### Steps

```
1. Extract text from PDF (PyPDF2)
        ↓
2. Split into chunks (LangChain RecursiveCharacterTextSplitter)
   chunk_size=1000, chunk_overlap=200
        ↓
3. Create embeddings for each chunk
   Model: sentence-transformers/all-MiniLM-L6-v2 (384-dim, lightweight)
        ↓
4. Store embeddings + chunk text into Qdrant Cloud
   Collection name: f"session_{session_id}"  ← per session isolation
        ↓
5. User asks question
        ↓
6. Embed the question using same model
        ↓
7. Qdrant similarity search → top 3-5 relevant chunks
        ↓
8. Build prompt with context + chat history
        ↓
9. Groq LLM generates answer (streamed)
        ↓
10. Save Q&A to PostgreSQL messages table
```

### LangGraph Node Flow

```
START
  │
  ▼
[embed_query]          ← embed user question
  │
  ▼
[retrieve_chunks]      ← Qdrant similarity search
  │
  ▼
[check_relevance]      ← are chunks relevant? (score threshold)
  │
  ├── NO  → [not_found_response]  ← "Not in document" message
  │
  └── YES → [generate_answer]     ← Groq LLM with context + history
                │
                ▼
            [save_to_db]          ← PostgreSQL insert
                │
                ▼
              END
```

### `pipeline/rag_pipeline.py` structure

```python
from langgraph.graph import StateGraph, END
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from groq import Groq

# State definition
class RAGState(TypedDict):
    question: str
    chunks: list[str]
    scores: list[float]
    context: str
    answer: str
    session_id: int
    chat_history: list[dict]
    found: bool

# Nodes: embed_query → retrieve → check → generate → save
# Build graph, compile, invoke
```

### Qdrant collection naming
- One collection per chat session: `f"doc_{session_id}"`
- Deleted when user deletes a session
- Prevents cross-user data leakage

---

## Phase 5 — Updated Streamlit UI

### Screen flow

```
App loads
    └──► Not logged in?  →  Login / Register screen
    └──► Logged in?      →  Main app
         ├── Sidebar: user's chat sessions list (like ChatGPT)
         │   ├── [+ New Chat] button
         │   ├── Session 1: "Summary of ML paper"
         │   ├── Session 2: "Contract questions"
         │   └── [Logout] button
         └── Main area: active chat session
             ├── PDF uploader (if new session)
             ├── Chat messages
             └── Question input
```

### UI changes from current app

| Current | Upgraded |
|---|---|
| No login | Login + Register screen |
| One chat only | Multiple sessions per user in sidebar |
| Session resets on refresh | History loaded from PostgreSQL |
| No user isolation | Each user sees only their own chats |
| New Chat clears everything | New Chat creates new DB session |

---

## Phase 6 — LLM Prompt (RAG-specific)

```python
SYSTEM_PROMPT = """You are DocMind AI, a precise document assistant.

Rules:
- Answer ONLY using the provided document context below.
- If the answer is not in the context, say exactly:
  "I don't have that information in this document."
- Never fabricate facts or use external knowledge.
- Be concise, accurate, and well-structured.
- Use bullet points or numbered lists when appropriate.

Document Context:
{context}
"""
```

---

## Dependencies to Add

```txt
# Existing (keep)
streamlit>=1.35.0
PyPDF2>=3.0.0
langchain-text-splitters>=0.3.0
groq>=0.11.0
python-dotenv>=1.0.0

# New additions
langgraph>=0.2.0
langchain>=0.3.0
langchain-groq>=0.2.0
sentence-transformers>=3.0.0
qdrant-client>=1.9.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.9
bcrypt>=4.0.0
tiktoken>=0.7.0
```

---

## Environment Variables (.env)

```env
GROQ_API_KEY=your-groq-key
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your-qdrant-key
DATABASE_URL=postgresql://user:password@host:5432/docmind
```

---

## Implementation Order (Day by Day)

### Day 1 — Foundation
- [ ] Set up PostgreSQL (Supabase free tier recommended)
- [ ] Create `core/database.py` and `core/models.py`
- [ ] Create all 3 tables (users, chat_sessions, messages)
- [ ] Build `core/auth.py` (register + login functions)
- [ ] Add login/register UI to `streamlit_app.py`

### Day 2 — RAG Pipeline
- [ ] Set up Qdrant Cloud (free tier)
- [ ] Build `core/token_counter.py`
- [ ] Build `pipeline/rag_pipeline.py` with LangGraph nodes
- [ ] Build `pipeline/router.py`
- [ ] Test with large PDF (> 20k tokens)

### Day 3 — Chat History + UI Polish
- [ ] Save all messages to PostgreSQL
- [ ] Load history from DB on session select
- [ ] Build session sidebar (list of user's chats)
- [ ] Add New Chat → creates new DB session
- [ ] Test multi-user isolation

### Day 4 — Deploy
- [ ] Push to GitHub
- [ ] Deploy to Streamlit Community Cloud
- [ ] Add all secrets in Streamlit dashboard
- [ ] End-to-end test with 2 different user accounts

---

## Free Services to Use

| Service | Free Tier | Use for |
|---|---|---|
| Supabase | 500MB PostgreSQL | Users + chat history |
| Qdrant Cloud | 1GB vector storage | RAG embeddings |
| Groq | Free API | LLM inference |
| Streamlit Cloud | Free hosting | UI deployment |

---

## Summary

| Feature | Current MVP | Upgraded |
|---|---|---|
| User accounts | ❌ | ✅ PostgreSQL |
| Chat history | Session only | ✅ Persistent DB |
| Multi-session | ❌ | ✅ Like ChatGPT |
| User isolation | ❌ | ✅ Per user_id |
| Large PDF support | ❌ Crashes | ✅ RAG Pipeline |
| Semantic search | Basic char freq | ✅ Sentence Transformers |
| Pipeline | In-memory only | ✅ Hybrid Router |
| Framework | None | ✅ LangGraph + LangChain |
