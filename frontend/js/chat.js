/**
 * frontend/js/chat.js
 * Chat list management, message rendering, and Q&A streaming.
 */

// ── State ─────────────────────────────────────────────────────────
let _chats       = [];
let _activeChatId = null;
let _isStreaming  = false;

// ── Load Chats ────────────────────────────────────────────────────
async function loadChats() {
  try {
    _chats = await apiGet('/chats');
    renderChatList(_chats);
  } catch (err) {
    console.error('Failed to load chats:', err);
  }
}

function renderChatList(chats) {
  const list = document.getElementById('chat-list');
  if (!list) return;

  if (chats.length === 0) {
    list.innerHTML = `
      <div style="text-align:center; padding:20px 12px; color:var(--text-muted); font-size:12px;">
        No chats yet.<br/>Click <strong>New Chat</strong> to start.
      </div>`;
    return;
  }

  list.innerHTML = chats.map(chat => `
    <div class="chat-item ${chat.chat_id === _activeChatId ? 'active' : ''}"
         id="chat-item-${chat.chat_id}"
         onclick="openChat('${chat.chat_id}')">
      <span class="chat-item-icon">💬</span>
      <div class="chat-item-body">
        <div class="chat-item-title truncate">${escapeHtml(chat.title)}</div>
        <div class="chat-item-meta">
          ${chat.message_count} msg${chat.message_count !== 1 ? 's' : ''}
          · ${formatRelative(chat.last_updated)}
          ${chat.document_name ? `· 📄 ${escapeHtml(chat.document_name.substring(0, 18))}` : ''}
        </div>
      </div>
      <div class="chat-item-actions">
        <button class="chat-item-action" onclick="openRenameModal(event, '${chat.chat_id}', '${escapeHtml(chat.title)}')" title="Rename">✏️</button>
        <button class="chat-item-action delete" onclick="deleteChat(event, '${chat.chat_id}')" title="Delete">🗑️</button>
      </div>
    </div>
  `).join('');
}

function filterChats(query) {
  const filtered = query
    ? _chats.filter(c => c.title.toLowerCase().includes(query.toLowerCase()))
    : _chats;
  renderChatList(filtered);
}

// ── Create New Chat ───────────────────────────────────────────────
async function createNewChat() {
  try {
    const res = await apiPost('/chats', { title: 'New Chat' });
    const chat = await res.json();
    if (!res.ok) throw new Error(chat.detail);

    _chats.unshift({
      chat_id: chat.chat_id,
      title: chat.title,
      message_count: 0,
      last_updated: chat.created_at,
      document_name: null,
    });
    renderChatList(_chats);
    await openChat(chat.chat_id);
    showToast('New chat created', 'success');
  } catch (err) {
    showToast('Failed to create chat: ' + err.message, 'error');
  }
}

// ── Open Chat ─────────────────────────────────────────────────────
async function openChat(chatId) {
  _activeChatId = chatId;
  renderChatList(_chats);

  const sendBtn = document.getElementById('send-btn');
  if (sendBtn) sendBtn.disabled = false;

  try {
    const chat = await apiGet(`/chats/${chatId}`);
    document.getElementById('active-chat-title').textContent = chat.title;
    document.getElementById('active-chat-sub').textContent =
      `${chat.pipeline_used ? `Pipeline: ${chat.pipeline_used.toUpperCase()} ·` : ''} DocMind AI`;

    renderMessages(chat.messages);

    // Notify upload module of active chat
    if (typeof setActiveChatForUpload === 'function') {
      setActiveChatForUpload(chatId, chat.document_id);
    }
  } catch (err) {
    showToast('Failed to load chat: ' + err.message, 'error');
  }
}

// ── Render Messages ───────────────────────────────────────────────
function renderMessages(messages) {
  const area = document.getElementById('messages-area');
  const welcome = document.getElementById('welcome-state');
  if (!area) return;

  // Remove all message rows (keep welcome-state element)
  area.querySelectorAll('.message-row').forEach(el => el.remove());

  if (messages.length === 0) {
    if (welcome) welcome.style.display = 'flex';
    return;
  }
  if (welcome) welcome.style.display = 'none';

  messages.forEach(msg => appendMessageBubble(msg.sender, msg.message, msg.timestamp, false));
  scrollToBottom();
}

function appendMessageBubble(sender, content, timestamp, animate = true) {
  const area = document.getElementById('messages-area');
  const welcome = document.getElementById('welcome-state');
  if (welcome) welcome.style.display = 'none';

  const isUser = sender === 'user';
  const row = document.createElement('div');
  row.className = `message-row ${sender} ${animate ? 'animate-in' : ''}`;
  row.dataset.sender = sender;

  const avatarContent = isUser
    ? (Auth.getUser()?.name?.[0] || 'U').toUpperCase()
    : '🧠';

  const time = timestamp ? formatTime(timestamp) : formatTime(new Date().toISOString());

  row.innerHTML = `
    <div class="msg-avatar ${sender}">${avatarContent}</div>
    <div class="msg-body">
      <div class="msg-bubble" data-raw="${escapeHtml(content)}">
        ${isUser ? escapeHtml(content) : renderMarkdown(content)}
      </div>
      <div class="msg-meta">
        <span class="msg-time">${time}</span>
        <div class="msg-actions">
          <button class="msg-action-btn" onclick="copyMessage(this)" title="Copy">📋</button>
          ${!isUser ? `<button class="msg-action-btn" onclick="regenerateResponse()" title="Regenerate">🔄</button>` : ''}
        </div>
      </div>
    </div>
  `;

  area.appendChild(row);

  // Apply syntax highlighting to code blocks
  row.querySelectorAll('pre code').forEach(block => {
    if (window.hljs) hljs.highlightElement(block);
  });

  return row;
}

// ── Streaming Message ─────────────────────────────────────────────
function startStreamingBubble() {
  const area = document.getElementById('messages-area');
  const row = document.createElement('div');
  row.className = 'message-row assistant animate-in';
  row.id = 'streaming-row';
  row.innerHTML = `
    <div class="msg-avatar assistant">🧠</div>
    <div class="msg-body">
      <div class="msg-bubble" id="streaming-bubble">
        <div class="typing-indicator">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      </div>
    </div>
  `;
  area.appendChild(row);
  scrollToBottom();
  return row;
}

function updateStreamingBubble(token) {
  const bubble = document.getElementById('streaming-bubble');
  if (!bubble) return;

  // Replace typing indicator on first token
  if (bubble.querySelector('.typing-indicator')) {
    bubble.innerHTML = '';
    bubble._raw = '';
  }
  bubble._raw = (bubble._raw || '') + token;
  bubble.innerHTML = renderMarkdown(bubble._raw);
  scrollToBottom();
}

function finaliseStreamingBubble() {
  const row = document.getElementById('streaming-row');
  if (!row) return;
  row.removeAttribute('id');

  const bubble = row.querySelector('.msg-bubble');
  const rawText = bubble._raw || bubble.textContent;
  bubble.dataset.raw = rawText;

  // Add actions
  const body = row.querySelector('.msg-body');
  const meta = document.createElement('div');
  meta.className = 'msg-meta';
  meta.innerHTML = `
    <span class="msg-time">${formatTime(new Date().toISOString())}</span>
    <div class="msg-actions">
      <button class="msg-action-btn" onclick="copyMessage(this)" title="Copy">📋</button>
      <button class="msg-action-btn" onclick="regenerateResponse()" title="Regenerate">🔄</button>
    </div>
  `;
  body.appendChild(meta);

  // Apply syntax highlighting
  row.querySelectorAll('pre code').forEach(b => window.hljs && hljs.highlightElement(b));
}

// ── Send Message ──────────────────────────────────────────────────
async function sendMessage() {
  if (_isStreaming || !_activeChatId) return;

  const input = document.getElementById('chat-input');
  const question = input.value.trim();
  if (!question) return;

  input.value = '';
  autoResizeTextarea(input);

  // Get active document id from upload module
  const activeDocId = (typeof getActiveDocId === 'function') ? getActiveDocId() : null;

  // Show user bubble
  appendMessageBubble('user', question, null, true);

  // Start streaming
  _isStreaming = true;
  document.getElementById('send-btn').disabled = true;

  const streamRow = startStreamingBubble();
  let pipelineInfo = null;

  await streamFetch(
    `/chats/${_activeChatId}/ask`,
    { question, document_id: activeDocId },
    (event) => {
      if (event.type === 'meta') {
        pipelineInfo = event;
        // Update topbar pipeline badge
        const sub = document.getElementById('active-chat-sub');
        if (sub && pipelineInfo.pipeline) {
          sub.textContent = `Pipeline: ${pipelineInfo.pipeline.toUpperCase()} · ${pipelineInfo.doc_name || ''}`;
        }
      } else if (event.type === 'token') {
        updateStreamingBubble(event.content);
      } else if (event.type === 'error') {
        updateStreamingBubble(event.content);
      }
    },
    () => {
      finaliseStreamingBubble();
      _isStreaming = false;
      document.getElementById('send-btn').disabled = false;
      // Refresh chat list to update message count + title
      loadChats();
    },
    (errMsg) => {
      finaliseStreamingBubble();
      showToast(errMsg, 'error');
      _isStreaming = false;
      document.getElementById('send-btn').disabled = false;
    }
  );
}

// ── Suggestion Chips ──────────────────────────────────────────────
function useSuggestion(text) {
  const input = document.getElementById('chat-input');
  if (!input || !_activeChatId) {
    showToast('Please create or select a chat first.', 'info');
    return;
  }
  input.value = text;
  autoResizeTextarea(input);
  sendMessage();
}

// ── Rename Chat ───────────────────────────────────────────────────
let _renamingChatId = null;

function openRenameModal(event, chatId, currentTitle) {
  event.stopPropagation();
  _renamingChatId = chatId;
  document.getElementById('rename-input').value = currentTitle;
  document.getElementById('rename-modal').classList.add('show');
  document.getElementById('rename-input').focus();
}

function closeRenameModal() {
  document.getElementById('rename-modal').classList.remove('show');
  _renamingChatId = null;
}

async function confirmRename() {
  const newTitle = document.getElementById('rename-input').value.trim();
  if (!newTitle || !_renamingChatId) return;

  try {
    await apiPatch(`/chats/${_renamingChatId}`, { title: newTitle });
    const idx = _chats.findIndex(c => c.chat_id === _renamingChatId);
    if (idx !== -1) _chats[idx].title = newTitle;
    if (_activeChatId === _renamingChatId) {
      document.getElementById('active-chat-title').textContent = newTitle;
    }
    renderChatList(_chats);
    closeRenameModal();
    showToast('Chat renamed', 'success');
  } catch (err) {
    showToast('Failed to rename: ' + err.message, 'error');
  }
}

// ── Delete Chat ───────────────────────────────────────────────────
async function deleteChat(event, chatId) {
  event.stopPropagation();
  if (!confirm('Delete this chat and all its messages?')) return;

  try {
    await apiDelete(`/chats/${chatId}`);
    _chats = _chats.filter(c => c.chat_id !== chatId);
    renderChatList(_chats);

    if (_activeChatId === chatId) {
      _activeChatId = null;
      clearChatView();
    }
    showToast('Chat deleted', 'success');
  } catch (err) {
    showToast('Failed to delete: ' + err.message, 'error');
  }
}

// ── Clear Chat View ───────────────────────────────────────────────
function clearChatView() {
  const area = document.getElementById('messages-area');
  area.querySelectorAll('.message-row').forEach(el => el.remove());
  const welcome = document.getElementById('welcome-state');
  if (welcome) welcome.style.display = 'flex';
  document.getElementById('active-chat-title').textContent = 'Select or create a chat';
  document.getElementById('active-chat-sub').textContent = 'DocMind AI · Ready';
  document.getElementById('send-btn').disabled = true;
}

// ── Copy Message ──────────────────────────────────────────────────
function copyMessage(btn) {
  const bubble = btn.closest('.msg-body').querySelector('.msg-bubble');
  const text = bubble.dataset.raw || bubble.textContent;
  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = '✅';
    setTimeout(() => { btn.textContent = '📋'; }, 1500);
  });
}

// ── Regenerate ────────────────────────────────────────────────────
async function regenerateResponse() {
  const area = document.getElementById('messages-area');
  const rows = area.querySelectorAll('.message-row');
  // Find last user message
  for (let i = rows.length - 1; i >= 0; i--) {
    if (rows[i].dataset.sender === 'user') {
      const question = rows[i].querySelector('.msg-bubble').dataset.raw
        || rows[i].querySelector('.msg-bubble').textContent;
      // Remove last assistant message
      if (rows[i + 1] && rows[i + 1].dataset.sender === 'assistant') {
        rows[i + 1].remove();
      }
      const activeDocId = (typeof getActiveDocId === 'function') ? getActiveDocId() : null;

      _isStreaming = true;
      document.getElementById('send-btn').disabled = true;
      startStreamingBubble();

      await streamFetch(
        `/chats/${_activeChatId}/ask`,
        { question, document_id: activeDocId },
        (event) => {
          if (event.type === 'token') updateStreamingBubble(event.content);
        },
        () => {
          finaliseStreamingBubble();
          _isStreaming = false;
          document.getElementById('send-btn').disabled = false;
        },
        (err) => {
          finaliseStreamingBubble();
          showToast(err, 'error');
          _isStreaming = false;
          document.getElementById('send-btn').disabled = false;
        }
      );
      break;
    }
  }
}

// ── Helpers ───────────────────────────────────────────────────────
function renderMarkdown(text) {
  if (!window.marked) return escapeHtml(text);
  return marked.parse(text, { breaks: true, gfm: true });
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function scrollToBottom() {
  const area = document.getElementById('messages-area');
  if (area) area.scrollTop = area.scrollHeight;
}

function autoResizeTextarea(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 160) + 'px';
}

function handleInputKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}

// Close modal on overlay click
document.addEventListener('click', (e) => {
  if (e.target.id === 'rename-modal') closeRenameModal();
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeRenameModal();
});
