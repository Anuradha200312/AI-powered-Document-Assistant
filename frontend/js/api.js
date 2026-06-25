/**
 * frontend/js/api.js
 * API client with automatic JWT auth header injection and 401 handling.
 */

const API_BASE = '/api/v1';

// ── Token Storage ─────────────────────────────────────────────────
const Auth = {
  getToken: () => localStorage.getItem('docmind_token'),
  setToken: (t) => localStorage.setItem('docmind_token', t),
  removeToken: () => localStorage.removeItem('docmind_token'),
  getUser: () => {
    try { return JSON.parse(localStorage.getItem('docmind_user') || 'null'); }
    catch { return null; }
  },
  setUser: (u) => localStorage.setItem('docmind_user', JSON.stringify(u)),
  removeUser: () => localStorage.removeItem('docmind_user'),
  isLoggedIn: () => !!localStorage.getItem('docmind_token'),
};

// ── Core Fetch Wrapper ─────────────────────────────────────────────
async function apiFetch(path, options = {}) {
  const token = Auth.getToken();
  const headers = { ...(options.headers || {}) };

  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = headers['Content-Type'] || 'application/json';
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    Auth.removeToken();
    Auth.removeUser();
    window.location.href = '/';
    throw new Error('Session expired. Please log in again.');
  }

  return res;
}

// Convenience helpers
async function apiGet(path) {
  const res = await apiFetch(path);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

async function apiPost(path, body, isFormData = false) {
  const res = await apiFetch(path, {
    method: 'POST',
    body: isFormData ? body : JSON.stringify(body),
  });
  return res;
}

async function apiPatch(path, body) {
  const res = await apiFetch(path, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

async function apiDelete(path) {
  const res = await apiFetch(path, { method: 'DELETE' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Request failed (${res.status})`);
  }
  return true;
}

// ── Streaming Fetch ────────────────────────────────────────────────
async function streamFetch(path, body, onEvent, onDone, onError) {
  try {
    const token = Auth.getToken();
    const res = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `Stream failed (${res.status})`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // keep incomplete line

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            onEvent(data);
            if (data.type === 'done') {
              onDone && onDone();
              return;
            }
          } catch (e) { /* ignore malformed SSE lines */ }
        }
      }
    }
    onDone && onDone();
  } catch (err) {
    onError && onError(err.message);
  }
}

// ── Toast Notification ─────────────────────────────────────────────
function showToast(message, type = 'info', durationMs = 3500) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icons[type] || '•'}</span><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    toast.style.transition = '0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, durationMs);
}

// ── Format Timestamp ──────────────────────────────────────────────
function formatTime(isoString) {
  const d = new Date(isoString);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatRelative(isoString) {
  const d = new Date(isoString);
  const now = new Date();
  const diff = now - d;
  if (diff < 60000) return 'just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return d.toLocaleDateString();
}
