# 🤖 AI Document Assistant

An AI-powered document Q&A app built with **Streamlit**, **ChromaDB**, **Sentence Transformers**, and **Groq LLM**. Upload any PDF and have an intelligent conversation about its contents — with full chat history and graceful handling of out-of-scope questions.

---

## ✨ Features

- 📤 **PDF Upload** — Upload any text-based PDF document
- 🔍 **Semantic Search** — ChromaDB + `all-MiniLM-L6-v2` embeddings find the most relevant chunks
- 🤖 **LLM Answers** — Groq `llama3-8b-8192` generates grounded, accurate answers
- 💬 **Chat History** — Full conversational context maintained within a session
- ❌ **Honest "Not Found"** — Detects when a question is out of scope and says so clearly
- 🎨 **Clean Dark UI** — Streamlit native chat interface with a polished theme

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| PDF Extraction | PyPDF2 |
| Text Chunking | LangChain `RecursiveCharacterTextSplitter` |
| Embeddings | `all-MiniLM-L6-v2` (SentenceTransformers, local) |
| Vector DB | ChromaDB (in-memory / ephemeral) |
| LLM | Groq API — `llama3-8b-8192` |
| Secrets | Streamlit Secrets / `.env` |

---

## 🚀 Local Setup

### 1. Clone the repository
```bash
git clone https://github.com/<your-username>/RagQA_PDF.git
cd RagQA_PDF
```

### 2. Create a virtual environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set your Groq API Key

**Option A — Streamlit secrets (recommended):**

Create the file `.streamlit/secrets.toml` (this file is git-ignored):
```toml
GROQ_API_KEY = "your-groq-api-key-here"
```

**Option B — Environment variable:**

Create a `.env` file in the project root:
```
GROQ_API_KEY=your-groq-api-key-here
```

> Get a free API key at [console.groq.com](https://console.groq.com)

### 5. Run the app
```bash
streamlit run streamlit_app.py
```

The app opens automatically at `http://localhost:8501`.

---

## ☁️ Deploy to Streamlit Community Cloud

1. **Push your code to GitHub** (make sure `.env` and `.streamlit/secrets.toml` are git-ignored)

2. **Go to** [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub

3. **Click "New app"** → select your repository → set:
   - **Main file path:** `streamlit_app.py`
   - **Branch:** `main`

4. **Add your secret:**
   - Click **"Advanced settings"** → **"Secrets"**
   - Add:
     ```toml
     GROQ_API_KEY = "your-groq-api-key-here"
     ```

5. **Click "Deploy"** — the app will be live in 1–2 minutes!

---

## 📂 Project Structure

```
RagQA_PDF/
├── streamlit_app.py        # ← Main Streamlit app (run this)
├── app.py                  # Flask version (kept for reference)
├── pdf_to_json.py          # Standalone invoice parser utility
├── requirements.txt        # Minimal dependencies (7 packages)
├── README.md
├── .gitignore
└── .streamlit/
    ├── config.toml         # App theme configuration
    └── secrets.toml        # Local API key (git-ignored)
```

---

## 💡 How It Works

```
User uploads PDF
    └──► PyPDF2 extracts text
         └──► Split into 1000-char overlapping chunks
              └──► Embedded with all-MiniLM-L6-v2
                   └──► Stored in ChromaDB (in-memory)

User asks a question
    └──► ChromaDB semantic search → top 3 similar chunks
         ├── Distance score > 1.5? → "Not found in document"
         └── Distance score OK? → Groq LLM generates answer
              └──► Answer displayed with full chat history context
```

---

## ⚠️ Limitations (MVP)

- PDF must contain **extractable text** (not scanned/image-only PDFs)
- Document data is **session-scoped** — uploading a new PDF starts fresh
- Max upload size: **50 MB** (configurable in `.streamlit/config.toml`)
- Answer length capped at **512 tokens** per response

---

## 📧 Contact

Built as part of the Techverse AI/ML Internship technical task.