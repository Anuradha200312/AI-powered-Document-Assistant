/**
 * frontend/js/app.js
 * Main application entry point — initialises everything.
 */

// ── Auth Guard ────────────────────────────────────────────────────
(function guardAuth() {
  if (!Auth.isLoggedIn()) {
    window.location.href = '/';
  }
})();

// ── Logout ────────────────────────────────────────────────────────
async function logout() {
  try {
    await apiFetch('/auth/logout', { method: 'POST' });
  } catch (_) { /* ignore */ }
  Auth.removeToken();
  Auth.removeUser();
  window.location.href = '/';
}

// ── User Profile ──────────────────────────────────────────────────
function initUserProfile() {
  const user = Auth.getUser();
  if (!user) return;

  const avatar = document.getElementById('user-avatar');
  const name   = document.getElementById('user-name');
  const email  = document.getElementById('user-email');

  if (avatar) avatar.textContent = (user.name?.[0] || 'U').toUpperCase();
  if (name)   name.textContent   = user.name || 'User';
  if (email)  email.textContent  = user.email || '';
}

// ── Initialise App ────────────────────────────────────────────────
async function initApp() {
  initUserProfile();

  // Configure marked.js
  if (window.marked) {
    marked.setOptions({
      breaks:   true,
      gfm:      true,
      headerIds: false,
    });
  }

  // Load chats
  await loadChats();
}

// ── Run on DOM ready ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', initApp);
