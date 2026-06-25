# 🧠 DocMind AI — AI-Powered Document Assistant

An AI-powered document Q&A app built with **Streamlit**, an **In-Memory Vector Store**, and **Groq LLM**. Upload any PDF and have an intelligent conversation about its contents — with full chat history and graceful handling of out-of-scope questions.

> Built as part of the **Techverse AI/ML Internship** technical task.

---

## ✨ Features

- 📤 **PDF Upload** — Upload any text-based PDF document
- 🔍 **Semantic Search** — In-memory cosine similarity search finds the most relevant chunks (no heavy DB required)
- 🤖 **LLM Answers** — Groq `llama-3.1-8b-instant` generates grounded, accurate answers
- 💬 **Chat History** — Full conversational context maintained within a session
- 📖 **Source Citations** — Each answer shows the exact document chunk it was based on
- ❌ **Honest "Not Found"** — Detects when a question is out of scope and says so clearly
- 🎨 **Premium Dark UI** — Custom-styled Streamlit interface with animations and glassmorphism

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| PDF Extraction | PyPDF2 |
| Text Chunking | LangChain `RecursiveCharacterTextSplitter` |
| Embeddings | TF-IDF Vectorizer (`scikit-learn`, fast & memory-only) |
| Vector DB | In-memory cosine similarity |
| LLM | Groq API — `llama-3.1-8b-instant` |
| Secrets | `.env` / Streamlit Secrets |

---

## 🚀 Local Setup

### 1. Clone the repository
```bash
git clone https://github.com/Anuradha200312/AI-powered-Document-Assistant.git
cd AI-powered-Document-Assistant
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

**Option A — `.env` file (recommended for local):**

Create a `.env` file in the project root:
```
GROQ_API_KEY=your-groq-api-key-here
```

**Option B — Streamlit secrets:**

Create the file `.streamlit/secrets.toml` (this file is git-ignored):
```toml
GROQ_API_KEY = "your-groq-api-key-here"
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
AI-powered-Document-Assistant/
├── streamlit_app.py        # ← Main Streamlit app (run this)
├── requirements.txt        # Minimal cloud-ready dependencies (6 packages)
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
    └──► PyPDF2 extracts raw text
         └──► Split into 1000-char overlapping chunks (200 char overlap)
              └──► Embedded using TF-IDF Vectorizer
                   └──► Stored in Streamlit session state

User asks a question
    └──► In-memory semantic search → top 3 most similar chunks via Cosine Similarity
         ├── Cosine similarity low? → "Not found in document"
         └── Similarity OK? → Groq LLM generates grounded answer
              └──► Answer + source chunk displayed with full chat history context
```

---

## ⚠️ Limitations (MVP)

- PDF must contain **extractable text** (not scanned/image-only PDFs)
- Document data is **session-scoped** — uploading a new PDF starts fresh
- Max upload size: **200 MB** (configurable in `.streamlit/config.toml`)
- Answer length capped at **512 tokens** per response

---

## 📧 Contact

**Anuradha** | Techverse AI/ML Internship Technical Task Submission