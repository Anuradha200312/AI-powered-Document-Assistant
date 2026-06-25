/**
 * frontend/js/auth.js
 * Login and registration logic for index.html
 */

// ── Tab Switching ─────────────────────────────────────────────────
function switchTab(tab) {
  const loginForm     = document.getElementById('login-form');
  const registerForm  = document.getElementById('register-form');
  const loginTab      = document.getElementById('tab-login');
  const registerTab   = document.getElementById('tab-register');
  const errorEl       = document.getElementById('auth-error');

  errorEl.classList.remove('show');

  if (tab === 'login') {
    loginForm.classList.remove('hidden');
    registerForm.classList.add('hidden');
    loginTab.classList.add('active');
    registerTab.classList.remove('active');
  } else {
    loginForm.classList.add('hidden');
    registerForm.classList.remove('hidden');
    registerTab.classList.add('active');
    loginTab.classList.remove('active');
  }
}

// ── Password Toggle ───────────────────────────────────────────────
function togglePassword(inputId, btn) {
  const input = document.getElementById(inputId);
  if (input.type === 'password') {
    input.type = 'text';
    btn.textContent = '🙈';
  } else {
    input.type = 'password';
    btn.textContent = '👁️';
  }
}

// ── Show Error ────────────────────────────────────────────────────
function showAuthError(message) {
  const el = document.getElementById('auth-error');
  el.textContent = message;
  el.classList.add('show');
}

// ── Login ─────────────────────────────────────────────────────────
async function handleLogin(event) {
  event.preventDefault();
  const email    = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;
  const btn      = document.getElementById('login-btn');
  const btnText  = document.getElementById('login-btn-text');

  document.getElementById('auth-error').classList.remove('show');
  btn.disabled = true;
  btnText.textContent = 'Signing in…';

  try {
    const res = await apiPost('/auth/login', { email, password });
    const data = await res.json().catch(() => ({ detail: res.statusText }));

    if (!res.ok) {
      showAuthError(data.detail || 'Login failed. Check your credentials.');
      return;
    }

    Auth.setToken(data.access_token);
    Auth.setUser({ user_id: data.user_id, name: data.name, email: data.email });
    showToast('Welcome back, ' + data.name + '! 🎉', 'success');

    setTimeout(() => { window.location.href = '/app'; }, 600);
  } catch (err) {
    showAuthError(err.message || 'Network error. Please try again.');
  } finally {
    btn.disabled = false;
    btnText.textContent = 'Sign In';
  }
}

// ── Register ──────────────────────────────────────────────────────
async function handleRegister(event) {
  event.preventDefault();
  const name     = document.getElementById('reg-name').value.trim();
  const email    = document.getElementById('reg-email').value.trim();
  const password = document.getElementById('reg-password').value;
  const btn      = document.getElementById('register-btn');
  const btnText  = document.getElementById('register-btn-text');

  document.getElementById('auth-error').classList.remove('show');

  if (password.length < 6) {
    showAuthError('Password must be at least 6 characters.');
    return;
  }

  btn.disabled = true;
  btnText.textContent = 'Creating account…';

  try {
    const res = await apiPost('/auth/register', { name, email, password });
    const data = await res.json().catch(() => ({ detail: res.statusText }));

    if (!res.ok) {
      showAuthError(data.detail || 'Registration failed. Please try again.');
      return;
    }

    Auth.setToken(data.access_token);
    Auth.setUser({ user_id: data.user_id, name: data.name, email: data.email });
    showToast('Account created! Welcome, ' + data.name + ' 🎉', 'success');

    setTimeout(() => { window.location.href = '/app'; }, 700);
  } catch (err) {
    showAuthError(err.message || 'Network error. Please try again.');
  } finally {
    btn.disabled = false;
    btnText.textContent = 'Create Account';
  }
}
