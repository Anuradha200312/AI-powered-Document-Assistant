import os
import uuid
import streamlit as st
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from groq import Groq

# ─────────────────────────────────────────────────────────────────
# Page Configuration
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DocMind AI — Document Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────
# Global Styles
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Global font */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }

/* ── Sidebar ─────────────────────────────── */
[data-testid="stSidebar"] {
    background: #0d0f1a !important;
    border-right: 1px solid #1e2035;
}
[data-testid="stSidebar"] * {
    color: #e2e8f0;
}

/* ── Upload area ─────────────────────────── */
[data-testid="stFileUploader"] {
    border: 2px dashed #2d3158;
    border-radius: 12px;
    padding: 8px;
    background: #131629;
    transition: border-color 0.2s;
}
[data-testid="stFileUploader"]:hover {
    border-color: #6C63FF;
}

/* ── Document info card ──────────────────── */
.doc-card {
    background: linear-gradient(135deg, #1a1d35 0%, #1e2245 100%);
    border: 1px solid #2d3158;
    border-left: 3px solid #6C63FF;
    border-radius: 10px;
    padding: 14px 16px;
    margin: 12px 0;
}
.doc-card .label {
    font-size: 11px;
    font-weight: 600;
    color: #6C63FF;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 4px;
}
.doc-card .value {
    font-size: 13px;
    color: #c8d0e7;
    font-weight: 500;
    word-break: break-all;
}
.doc-stat {
    display: flex;
    gap: 12px;
    margin-top: 10px;
}
.stat-pill {
    background: #6C63FF22;
    border: 1px solid #6C63FF44;
    border-radius: 20px;
    padding: 3px 10px;
    font-size: 11px;
    color: #a89cff;
    font-weight: 500;
}

/* ── Welcome screen ──────────────────────── */
.hero {
    text-align: center;
    padding: 48px 24px 32px;
}
.hero-badge {
    display: inline-block;
    background: #6C63FF1a;
    border: 1px solid #6C63FF44;
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 12px;
    color: #a89cff;
    font-weight: 500;
    margin-bottom: 20px;
    letter-spacing: 0.5px;
}
.hero h1 {
    font-size: 42px;
    font-weight: 700;
    color: #f0f4ff;
    margin: 0 0 12px;
    line-height: 1.2;
}
.hero h1 span {
    background: linear-gradient(135deg, #6C63FF, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.hero p {
    font-size: 17px;
    color: #8892aa;
    max-width: 520px;
    margin: 0 auto 32px;
    line-height: 1.6;
}

/* ── Feature cards ───────────────────────── */
.feature-card {
    background: #131629;
    border: 1px solid #1e2240;
    border-radius: 14px;
    padding: 24px;
    height: 100%;
    transition: border-color 0.2s, transform 0.2s;
}
.feature-card:hover {
    border-color: #6C63FF66;
    transform: translateY(-2px);
}
.feature-icon {
    font-size: 28px;
    margin-bottom: 14px;
    display: block;
}
.feature-card h3 {
    font-size: 15px;
    font-weight: 600;
    color: #e2e8f0;
    margin: 0 0 8px;
}
.feature-card p {
    font-size: 13px;
    color: #6b7399;
    margin: 0;
    line-height: 1.6;
}

/* ── Chat area header ────────────────────── */
.chat-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px 20px;
    background: #131629;
    border: 1px solid #1e2240;
    border-radius: 12px;
    margin-bottom: 20px;
}
.chat-header-icon {
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, #6C63FF, #a78bfa);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    flex-shrink: 0;
}
.chat-header-text h3 {
    font-size: 15px;
    font-weight: 600;
    color: #e2e8f0;
    margin: 0 0 2px;
}
.chat-header-text p {
    font-size: 12px;
    color: #6b7399;
    margin: 0;
}
.status-dot {
    width: 8px;
    height: 8px;
    background: #22c55e;
    border-radius: 50%;
    display: inline-block;
    margin-right: 5px;
    box-shadow: 0 0 6px #22c55e88;
}

/* ── Upload prompt ───────────────────────── */
.upload-prompt {
    text-align: center;
    padding: 48px 24px;
    border: 2px dashed #1e2240;
    border-radius: 16px;
    margin-top: 24px;
}
.upload-prompt h3 {
    font-size: 18px;
    color: #6b7399;
    margin: 12px 0 8px;
}
.upload-prompt p {
    font-size: 13px;
    color: #4a5170;
    margin: 0;
}

/* ── Sidebar brand ───────────────────────── */
.sidebar-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px 0 20px;
    border-bottom: 1px solid #1e2035;
    margin-bottom: 20px;
}
.brand-icon {
    font-size: 24px;
}
.brand-name {
    font-size: 18px;
    font-weight: 700;
    color: #f0f4ff;
    letter-spacing: -0.3px;
}
.brand-name span {
    color: #6C63FF;
}

/* ── Section label ───────────────────────── */
.section-label {
    font-size: 11px;
    font-weight: 600;
    color: #4a5170;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin: 20px 0 10px;
}

/* ── Tips box ────────────────────────────── */
.tips-box {
    background: #0d0f1a;
    border: 1px solid #1e2035;
    border-radius: 10px;
    padding: 14px;
    margin-top: 8px;
}
.tips-box p {
    font-size: 12px;
    color: #4a5170;
    margin: 0 0 6px;
    line-height: 1.5;
}
.tips-box p:last-child { margin: 0; }

/* ── Powered by ──────────────────────────── */
.powered-by {
    font-size: 11px;
    color: #2d3158;
    text-align: center;
    padding: 12px 0 4px;
    border-top: 1px solid #1e2035;
    margin-top: 16px;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# API Key
# ─────────────────────────────────────────────────────────────────
def get_api_key() -> str:
    try:
        return st.secrets["GROQ_API_KEY"]
    except (KeyError, FileNotFoundError):
        key = os.getenv("GROQ_API_KEY", "")
        if not key:
            st.error(
                "⚠️ **Groq API key not found.**\n\n"
                "Add `GROQ_API_KEY` to `.streamlit/secrets.toml` (local) "
                "or Streamlit Cloud Secrets Manager."
            )
            st.stop()
        return key


# ─────────────────────────────────────────────────────────────────
# Cached Resources
# ─────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="⚙️ Loading embedding model…")
def get_embedding_function():
    """Use ChromaDB's built-in ONNX embedding — no extra package needed."""
    return DefaultEmbeddingFunction()


@st.cache_resource
def get_groq_client():
    return Groq(api_key=get_api_key())


# ─────────────────────────────────────────────────────────────────
# Session State
# ─────────────────────────────────────────────────────────────────
def init_session_state():
    defaults = {
        "chat_history": [],
        "collection": None,
        "processed_filename": None,
        "chunks_count": 0,
        "chroma_client": chromadb.EphemeralClient(),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ─────────────────────────────────────────────────────────────────
# PDF Processing
# ─────────────────────────────────────────────────────────────────
def process_pdf(uploaded_file) -> tuple[bool, str | int]:
    try:
        reader = PdfReader(uploaded_file)
        full_text = "".join(page.extract_text() or "" for page in reader.pages)

        if not full_text.strip():
            return False, "This PDF has no extractable text (may be a scanned image)."

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200, length_function=len
        )
        chunks = [doc.page_content for doc in splitter.create_documents([full_text])]

        if not chunks:
            return False, "Could not split PDF into chunks."

        # Reset collection
        try:
            st.session_state.chroma_client.delete_collection("pdf_collection")
        except Exception:
            pass

        collection = st.session_state.chroma_client.create_collection(
            name="pdf_collection",
            embedding_function=get_embedding_function(),
        )
        collection.add(documents=chunks, ids=[str(uuid.uuid4()) for _ in chunks])

        st.session_state.collection = collection
        st.session_state.chunks_count = len(chunks)
        return True, len(chunks)

    except Exception as e:
        return False, f"Error processing PDF: {str(e)}"


# ─────────────────────────────────────────────────────────────────
# Answer Generation
# ─────────────────────────────────────────────────────────────────
SIMILARITY_THRESHOLD = 1.5
MAX_HISTORY_TURNS = 6


def get_answer(question: str) -> str:
    results = st.session_state.collection.query(
        query_texts=[question],
        n_results=3,
        include=["documents", "distances"],
    )

    docs = results["documents"][0]
    distances = results["distances"][0]

    if not docs or (distances and distances[0] > SIMILARITY_THRESHOLD):
        return (
            "I couldn't find relevant information about that in the uploaded document. "
            "Please try rephrasing, or ask about something covered in the document."
        )

    context = "\n\n---\n\n".join(docs)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a precise AI assistant. Answer questions ONLY based on the "
                "document context provided. If the answer is not in the context, say "
                "'I don't have that information in this document.' "
                "Do NOT fabricate facts. Be concise and accurate."
            ),
        },
        *st.session_state.chat_history[-MAX_HISTORY_TURNS:],
        {
            "role": "user",
            "content": f"Document Context:\n{context}\n\nQuestion: {question}",
        },
    ]

    response = get_groq_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.3,
        max_tokens=512,
    )
    return response.choices[0].message.content.strip()


# ─────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        # Brand
        st.markdown("""
        <div class="sidebar-brand">
            <span class="brand-icon">🧠</span>
            <span class="brand-name">Doc<span>Mind</span> AI</span>
        </div>
        """, unsafe_allow_html=True)

        # Upload
        st.markdown('<div class="section-label">📂 Document</div>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Upload PDF",
            type=["pdf"],
            label_visibility="collapsed",
            help="Upload a PDF to start asking questions about it.",
        )

        # Process new PDF
        if uploaded_file is not None:
            if uploaded_file.name != st.session_state.processed_filename:
                with st.spinner("🔄 Indexing document…"):
                    success, result = process_pdf(uploaded_file)
                if success:
                    st.session_state.processed_filename = uploaded_file.name
                    st.session_state.chat_history = []
                    st.success(f"✅ Indexed **{result}** chunks")
                else:
                    st.error(f"❌ {result}")

        # Document info
        if st.session_state.processed_filename:
            fname = st.session_state.processed_filename
            short_name = fname if len(fname) <= 28 else fname[:25] + "…"
            st.markdown(f"""
            <div class="doc-card">
                <div class="label">Active Document</div>
                <div class="value">📄 {short_name}</div>
                <div class="doc-stat">
                    <span class="stat-pill">📊 {st.session_state.chunks_count} chunks</span>
                    <span class="stat-pill">💬 {len(st.session_state.chat_history)//2} turns</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🗑️ Clear Chat", use_container_width=True, type="secondary"):
                st.session_state.chat_history = []
                st.rerun()

        # Tips
        st.markdown('<div class="section-label">💡 Tips</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="tips-box">
            <p>📌 Ask specific questions for best results.</p>
            <p>🔁 Follow-up questions use previous context.</p>
            <p>📄 Upload a new PDF to switch documents.</p>
        </div>
        """, unsafe_allow_html=True)

        # Powered by
        st.markdown("""
        <div class="powered-by">
            Groq · ChromaDB · Streamlit
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# Welcome Screen
# ─────────────────────────────────────────────────────────────────
def render_welcome():
    st.markdown("""
    <div class="hero">
        <div class="hero-badge">✨ AI-Powered Document Analysis</div>
        <h1>Ask anything about<br>your <span>PDF document</span></h1>
        <p>Upload a PDF and have an intelligent conversation about its contents.
        Powered by Groq's ultra-fast LLM inference.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3, gap="medium")
    cards = [
        ("📤", "Upload Any PDF",
         "Reports, contracts, research papers, books — any text-based PDF works instantly."),
        ("🔍", "Semantic Search",
         "Finds the most relevant sections from your document using vector similarity search."),
        ("🧠", "Grounded Answers",
         "LLM answers are strictly based on your document — no hallucinations, honest when unsure."),
    ]
    for col, (icon, title, desc) in zip([col1, col2, col3], cards):
        with col:
            st.markdown(f"""
            <div class="feature-card">
                <span class="feature-icon">{icon}</span>
                <h3>{title}</h3>
                <p>{desc}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("""
    <div class="upload-prompt">
        <div style="font-size: 40px;">☝️</div>
        <h3>Upload a PDF from the sidebar to get started</h3>
        <p>Your document is processed locally — nothing is stored permanently.</p>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# Chat Screen
# ─────────────────────────────────────────────────────────────────
def render_chat():
    fname = st.session_state.processed_filename
    short_name = fname if len(fname) <= 40 else fname[:37] + "…"

    # Chat header
    st.markdown(f"""
    <div class="chat-header">
        <div class="chat-header-icon">📄</div>
        <div class="chat-header-text">
            <h3>{short_name}</h3>
            <p><span class="status-dot"></span>Ready · {st.session_state.chunks_count} chunks indexed · Ask anything about this document</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Empty state
    if not st.session_state.chat_history:
        st.markdown("""
        <div style="text-align:center; padding: 40px 0; color: #4a5170;">
            <div style="font-size:36px; margin-bottom:12px;">💬</div>
            <p style="font-size:15px; margin:0;">No messages yet — type a question below to begin.</p>
        </div>
        """, unsafe_allow_html=True)

    # Chat messages
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if question := st.chat_input("Ask a question about your document…"):
        with st.chat_message("user"):
            st.markdown(question)
        st.session_state.chat_history.append({"role": "user", "content": question})

        with st.chat_message("assistant"):
            with st.spinner("Searching document…"):
                answer = get_answer(question)
            st.markdown(answer)
        st.session_state.chat_history.append({"role": "assistant", "content": answer})


# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────
def main():
    init_session_state()
    render_sidebar()

    if st.session_state.processed_filename is None:
        render_welcome()
    else:
        render_chat()


if __name__ == "__main__":
    main()
