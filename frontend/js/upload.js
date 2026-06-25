/**
 * frontend/js/upload.js
 * PDF upload with drag-and-drop, progress tracking, and status polling.
 */

// ── State ─────────────────────────────────────────────────────────
let _activeChatId   = null;
let _activeDocId    = null;
let _pollInterval   = null;
let _allDocuments   = [];

// Called by chat.js when a chat is activated
function setActiveChatForUpload(chatId, docId) {
  _activeChatId = chatId;
  _activeDocId  = docId;
  loadDocumentHistory();
  if (docId) updateActiveDocCard(docId);
}

// Called by chat.js / rag.js to get active doc_id
function getActiveDocId() {
  return _activeDocId;
}

// ── Drag & Drop ───────────────────────────────────────────────────
function handleDragOver(event) {
  event.preventDefault();
  document.getElementById('upload-zone').classList.add('drag-over');
}

function handleDragLeave(event) {
  document.getElementById('upload-zone').classList.remove('drag-over');
}

function handleDrop(event) {
  event.preventDefault();
  document.getElementById('upload-zone').classList.remove('drag-over');
  const files = event.dataTransfer.files;
  if (files.length > 0) processFile(files[0]);
}

function handleFileSelect(event) {
  const file = event.target.files[0];
  if (file) processFile(file);
  // Reset input so same file can be re-uploaded
  event.target.value = '';
}

// ── Process File ──────────────────────────────────────────────────
async function processFile(file) {
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    showToast('Only PDF files are supported.', 'error');
    return;
  }
  if (file.size > 50 * 1024 * 1024) {
    showToast('File too large. Maximum size is 50 MB.', 'error');
    return;
  }
  if (!_activeChatId) {
    showToast('Please create or select a chat first, then upload a PDF.', 'info');
    return;
  }

  showUploadProgress(file.name);

  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('chat_id', _activeChatId);

    const res = await apiFetch('/documents/upload', { method: 'POST', body: formData });
    const data = await res.json();

    if (!res.ok) {
      hideUploadProgress();
      showToast(data.detail || 'Upload failed.', 'error');
      return;
    }

    _activeDocId = data.document_id;
    setUploadStatusText('Processing document…', data.document_id, '');
    startPolling(data.document_id);

  } catch (err) {
    hideUploadProgress();
    showToast('Upload error: ' + err.message, 'error');
  }
}

// ── Status Polling ────────────────────────────────────────────────
function startPolling(documentId) {
  if (_pollInterval) clearInterval(_pollInterval);

  _pollInterval = setInterval(async () => {
    try {
      const doc = await apiGet(`/documents/${documentId}/status`);
      updatePollUI(doc);

      if (doc.processing_status === 'ready' || doc.processing_status === 'error') {
        clearInterval(_pollInterval);
        _pollInterval = null;

        if (doc.processing_status === 'ready') {
          showToast(`✅ "${escapeHtml(document.getElementById('upload-filename').textContent)}" ready!`, 'success');
          _activeDocId = documentId;
          await loadDocumentHistory();
          updateActiveDocCard(documentId, doc);
          setTimeout(hideUploadProgress, 1500);
        } else {
          showToast('Processing failed: ' + (doc.error_message || 'Unknown error'), 'error');
          hideUploadProgress();
        }
      }
    } catch (err) {
      console.warn('Poll error:', err);
    }
  }, 2000);
}

function updatePollUI(doc) {
  const tokenEl = document.getElementById('upload-token-count');
  if (tokenEl && doc.token_count > 0) {
    tokenEl.textContent = `${doc.token_count.toLocaleString()} tokens`;
  }

  const badge = document.getElementById('upload-status-badge');
  const statusText = document.getElementById('upload-status-text');

  const statusMap = {
    pending:    { badge: 'Queued',      class: 'badge-warning', text: 'Queued for processing…' },
    processing: { badge: 'Processing',  class: 'badge-brand',   text: 'Chunking and embedding…' },
    ready:      { badge: 'Ready ✓',     class: 'badge-success', text: 'Document is ready!' },
    error:      { badge: 'Error',       class: 'badge-error',   text: doc.error_message || 'Processing failed.' },
  };

  const info = statusMap[doc.processing_status] || statusMap.pending;
  if (badge) {
    badge.className = `badge ${info.class}`;
    badge.textContent = info.badge;
  }
  if (statusText) statusText.textContent = info.text;

  if (doc.processing_status === 'ready' && doc.pipeline_used) {
    const pipeEl = document.createElement('span');
    pipeEl.className = `badge ${doc.pipeline_used === 'rag' ? 'badge-brand' : 'badge-success'}`;
    pipeEl.textContent = `Pipeline: ${doc.pipeline_used.toUpperCase()}`;
    if (statusText && !statusText.parentNode.querySelector('.pipeline-badge')) {
      pipeEl.classList.add('pipeline-badge');
      statusText.parentNode.appendChild(pipeEl);
    }
  }
}

// ── Progress UI ───────────────────────────────────────────────────
function showUploadProgress(filename) {
  document.getElementById('upload-zone').style.display = 'none';
  const prog = document.getElementById('upload-progress');
  prog.classList.add('show');
  document.getElementById('upload-filename').textContent =
    filename.length > 30 ? filename.substring(0, 27) + '…' : filename;
  document.getElementById('upload-status-badge').className = 'badge badge-info';
  document.getElementById('upload-status-badge').textContent = 'Uploading';
  document.getElementById('upload-status-text').textContent = 'Uploading file…';
  document.getElementById('upload-token-count').textContent = '';

  const fill = document.getElementById('progress-fill');
  fill.classList.add('indeterminate');
}

function hideUploadProgress() {
  const prog = document.getElementById('upload-progress');
  prog.classList.remove('show');
  document.getElementById('upload-zone').style.display = 'block';
  const fill = document.getElementById('progress-fill');
  fill.classList.remove('indeterminate');
  fill.style.width = '0%';
  // Clear old pipeline badge
  prog.querySelectorAll('.pipeline-badge').forEach(el => el.remove());
}

function setUploadStatusText(text, docId, tokens) {
  document.getElementById('upload-status-text').textContent = text;
  if (tokens) document.getElementById('upload-token-count').textContent = tokens;
}

// ── Document History ──────────────────────────────────────────────
async function loadDocumentHistory() {
  try {
    _allDocuments = await apiGet('/documents');
    renderDocHistory();
  } catch (err) {
    console.warn('Could not load document history:', err);
  }
}

function renderDocHistory() {
  const section = document.getElementById('doc-history-section');
  const list    = document.getElementById('doc-history-list');
  if (!list) return;

  const chatDocs = _allDocuments.filter(d => d.chat_id === _activeChatId);
  const otherDocs = _allDocuments.filter(d => d.chat_id !== _activeChatId);
  const displayDocs = [...chatDocs, ...otherDocs].slice(0, 10);

  if (displayDocs.length === 0) {
    if (section) section.classList.add('hidden');
    return;
  }

  if (section) section.classList.remove('hidden');

  list.innerHTML = displayDocs.map(doc => `
    <div class="doc-history-item ${doc.document_id === _activeDocId ? 'active' : ''}"
         onclick="selectDocument('${doc.document_id}')">
      <span class="doc-history-item-icon">📄</span>
      <div class="doc-history-item-body">
        <div class="doc-history-item-name">${escapeHtml(doc.filename)}</div>
        <div class="doc-history-item-meta">
          ${doc.token_count > 0 ? doc.token_count.toLocaleString() + ' tokens · ' : ''}
          ${doc.pipeline_used !== 'pending' ? doc.pipeline_used.toUpperCase() + ' · ' : ''}
          <span class="${doc.processing_status === 'ready' ? 'status-ok' : ''}">${doc.processing_status}</span>
        </div>
      </div>
      <button class="chat-item-action delete" onclick="deleteDocument(event, '${doc.document_id}')" title="Delete">🗑️</button>
    </div>
  `).join('');
}

function selectDocument(docId) {
  _activeDocId = docId;
  renderDocHistory();
  const doc = _allDocuments.find(d => d.document_id === docId);
  if (doc) updateActiveDocCard(docId, doc);
  showToast('Active document switched', 'info');
}

async function deleteDocument(event, docId) {
  event.stopPropagation();
  if (!confirm('Delete this document? This will also remove its vectors from Qdrant.')) return;
  try {
    await apiDelete(`/documents/${docId}`);
    _allDocuments = _allDocuments.filter(d => d.document_id !== docId);
    if (_activeDocId === docId) {
      _activeDocId = null;
      document.getElementById('active-doc-card').classList.add('hidden');
    }
    renderDocHistory();
    showToast('Document deleted', 'success');
  } catch (err) {
    showToast('Delete failed: ' + err.message, 'error');
  }
}

// ── Active Doc Card ───────────────────────────────────────────────
function updateActiveDocCard(docId, doc) {
  const card = document.getElementById('active-doc-card');
  if (!card) return;

  const d = doc || _allDocuments.find(x => x.document_id === docId);
  if (!d) return;

  const pipeClass = d.pipeline_used === 'rag' ? 'pipeline-rag' : 'pipeline-direct';
  const statusClass = `status-${d.processing_status}`;

  card.innerHTML = `
    <div class="doc-info-card">
      <div class="doc-info-name">📄 ${escapeHtml(d.filename)}</div>
      <div class="doc-info-stats">
        ${d.token_count > 0 ? `<span class="doc-stat-pill tokens">🔢 ${d.token_count.toLocaleString()} tokens</span>` : ''}
        ${d.pipeline_used !== 'pending' ? `<span class="doc-stat-pill ${pipeClass}">⚡ ${d.pipeline_used.toUpperCase()}</span>` : ''}
        <span class="doc-stat-pill ${statusClass}">
          ${d.processing_status === 'ready' ? '✅' : d.processing_status === 'error' ? '❌' : '⏳'} ${d.processing_status}
        </span>
      </div>
    </div>
  `;
  card.classList.remove('hidden');
}
