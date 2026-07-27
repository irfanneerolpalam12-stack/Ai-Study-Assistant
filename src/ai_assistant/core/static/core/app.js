/**
 * AI Study Assistant — Chat Application Controller
 * Full PDF RAG pipeline: upload → extract → embed → query → LLM
 */

/* ═══════════════════════════════════════════════════════════════════════════
   API Utility Layer
   ═══════════════════════════════════════════════════════════════════════════ */
const API = (() => {
  const BASE = '/api';

  function getToken()  { return localStorage.getItem('access_token'); }
  function setTokens(access, refresh) {
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
  }
  function clearTokens() {
    ['access_token','refresh_token','user'].forEach(k => localStorage.removeItem(k));
  }

  async function refreshAccessToken() {
    const refresh = localStorage.getItem('refresh_token');
    if (!refresh) throw new Error('No refresh token');
    const res = await fetch(`${BASE}/token/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    });
    if (!res.ok) throw new Error('Token refresh failed');
    const data = await res.json();
    localStorage.setItem('access_token', data.access);
    return data.access;
  }

  async function request(endpoint, options = {}, retry = true) {
    const token = getToken();
    const headers = { ...options.headers };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    const res = await fetch(`${BASE}${endpoint}`, { ...options, headers });

    if (res.status === 401 && retry) {
      try {
        await refreshAccessToken();
        return request(endpoint, options, false);
      } catch {
        clearTokens();
        window.location.reload();
        return;
      }
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: res.statusText }));
      throw { status: res.status, data: err };
    }

    if (res.status === 204) return null;
    return res.json();
  }

  return {
    get:    url       => request(url, { method: 'GET' }),
    post:   (url, body) => request(url, {
      method: 'POST',
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),
    patch:  (url, body) => request(url, { method: 'PATCH', body: JSON.stringify(body) }),
    delete: url       => request(url, { method: 'DELETE' }),
    setTokens, clearTokens, getToken,
  };
})();


/* ═══════════════════════════════════════════════════════════════════════════
   Toast Notifications
   ═══════════════════════════════════════════════════════════════════════════ */
function showToast(message, type = 'info', duration = 3500) {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const icons = { success: '✅', error: '❌', info: '💡' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icons[type] || '💡'}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}


/* ═══════════════════════════════════════════════════════════════════════════
   Auth Module
   ═══════════════════════════════════════════════════════════════════════════ */
const Auth = (() => {
  function isLoggedIn() { return !!API.getToken(); }

  function getUser() {
    try { return JSON.parse(localStorage.getItem('user') || 'null'); }
    catch { return null; }
  }

  function setUser(user) { localStorage.setItem('user', JSON.stringify(user)); }

  async function login(email, password) {
    const data = await API.post('/auth/login/', { email, password });
    API.setTokens(data.access, data.refresh);
    setUser(data.user);
    return data.user;
  }

  async function register(email, name, password, password2) {
    const data = await API.post('/auth/register/', { email, name, password, password2 });
    API.setTokens(data.access, data.refresh);
    setUser(data.user);
    return data.user;
  }

  async function googleLogin(accessToken) {
    const data = await API.post('/auth/google/', { access_token: accessToken });
    API.setTokens(data.access, data.refresh);
    setUser(data.user);
    return data.user;
  }

  function logout() {
    API.clearTokens();
    window.location.reload();
  }

  return { isLoggedIn, getUser, setUser, login, register, googleLogin, logout };
})();


/* ═══════════════════════════════════════════════════════════════════════════
   Auth UI
   ═══════════════════════════════════════════════════════════════════════════ */
function setupAuthUI() {
  const overlay  = document.getElementById('auth-overlay');
  const errEl    = document.getElementById('auth-error');
  const tabs     = document.querySelectorAll('.auth-tab');
  const loginDiv = document.getElementById('login-form');
  const regDiv   = document.getElementById('register-form');

  function setError(msg) { errEl.textContent = msg || ''; }

  // Tab switching
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      setError('');
      if (tab.dataset.tab === 'login') {
        loginDiv.style.display = '';
        regDiv.style.display   = 'none';
      } else {
        loginDiv.style.display = 'none';
        regDiv.style.display   = '';
      }
    });
  });

  // Login
  document.getElementById('btn-login').addEventListener('click', async () => {
    const email    = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;
    if (!email || !password) { setError('Please fill in all fields.'); return; }
    setError('');
    const btn = document.getElementById('btn-login');
    btn.disabled = true; btn.textContent = 'Signing in…';
    try {
      const user = await Auth.login(email, password);
      overlay.remove();
      initApp(user);
    } catch (e) {
      setError(e?.data?.error || e?.data?.detail || 'Login failed. Check your credentials.');
      btn.disabled = false; btn.textContent = 'Sign In →';
    }
  });

  // Enter key on password
  document.getElementById('login-password').addEventListener('keydown', e => {
    if (e.key === 'Enter') document.getElementById('btn-login').click();
  });

  // ── Google Login ─────────────────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", () => {
      const googleBtn = document.getElementById('google-signin-btn');
      
      if (googleBtn) {
          googleBtn.addEventListener('click', (e) => {
              e.preventDefault();
              
              if (!window.google || !window.google.accounts || !window.google.accounts.oauth2) {
                  console.error("Google Identity SDK has not loaded yet.");
                  alert("Google Sign-In is still initializing. Please try again in a moment.");
                  return;
              }

              if (!window.GOOGLE_CLIENT_ID || window.GOOGLE_CLIENT_ID === "") {
                  console.error("CRITICAL: window.GOOGLE_CLIENT_ID is empty or missing.");
                  return;
              }

              const tokenClient = google.accounts.oauth2.initTokenClient({
                  client_id: window.GOOGLE_CLIENT_ID,
                  scope: 'email profile openid',
                  callback: async (tokenResponse) => {
                      if (tokenResponse && tokenResponse.access_token) {
                          // Auth token received — forward to Django backend
                          try {
                              const response = await fetch('/api/auth/google/', {
                                  method: 'POST',
                                  headers: {
                                      'Content-Type': 'application/json',
                                  },
                                  body: JSON.stringify({ access_token: tokenResponse.access_token })
                              });
                              
                              const data = await response.json();
                              if (response.ok) {
                                  // Login successful — transition SPA state
                                  API.setTokens(data.access, data.refresh);
                                  setUser(data.user);
                                  overlay.remove();
                                  initApp(data.user);
                              } else {
                                  console.error("Google authentication failed. Please try again.");
                                  setError(data?.error || 'Google login failed. Please try again.');
                              }
                          } catch (err) {
                              console.error("Network error during Google authentication.");
                              setError('A network error occurred. Please check your connection.');
                          }
                      }
                  }
              });

              tokenClient.requestAccessToken();
          });
      } else {
          // btn-google-signin not found — likely auth overlay is not rendered
      }
  });

  // Register
  document.getElementById('btn-register').addEventListener('click', async () => {
    const name  = document.getElementById('reg-name').value.trim();
    const email = document.getElementById('reg-email').value.trim();
    const pw1   = document.getElementById('reg-password').value;
    const pw2   = document.getElementById('reg-password2').value;
    if (!name || !email || !pw1 || !pw2) { setError('Please fill in all fields.'); return; }
    if (pw1 !== pw2) { setError('Passwords do not match.'); return; }
    setError('');
    const btn = document.getElementById('btn-register');
    btn.disabled = true; btn.textContent = 'Creating account…';
    try {
      const user = await Auth.register(email, name, pw1, pw2);
      overlay.remove();
      initApp(user);
    } catch (e) {
      const errors = e?.data;
      const msg = errors
        ? Object.values(errors).flat().join(' ')
        : 'Registration failed. Try again.';
      setError(msg);
      btn.disabled = false; btn.textContent = 'Create Account →';
    }
  });
}


/* ═══════════════════════════════════════════════════════════════════════════
   Chat Module — Core State Machine
   ═══════════════════════════════════════════════════════════════════════════ */
const ChatModule = (() => {
  let currentChatId  = null;
  let currentDocId   = null;   // ID of uploaded document for RAG
  let stagedFile     = null;   // File waiting to be uploaded when sending message
  let isWaiting      = false;  // Prevent double-sends

  // ── Helpers ──────────────────────────────────────────────────────────────

  function getMessagesEl()   { return document.getElementById('chat-messages'); }
  function getEmptyStateEl() { return document.getElementById('chat-empty-state'); }

  function showMessages() {
    const msgs = getMessagesEl();
    const empty = getEmptyStateEl();
    if (msgs)  msgs.style.display = 'flex';
    if (msgs)  msgs.style.flexDirection = 'column';
    if (empty) empty.style.display = 'none';
  }

  function showEmpty() {
    const msgs = getMessagesEl();
    const empty = getEmptyStateEl();
    if (msgs)  { msgs.style.display = 'none'; msgs.innerHTML = ''; }
    if (empty) empty.style.display = 'flex';
  }

  function showActiveContext(doc) {
    const bar = document.getElementById('active-context-bar');
    const nameEl = document.getElementById('active-context-name');
    if (bar && nameEl && doc) {
      bar.style.display = 'flex';
      nameEl.textContent = doc.title || 'Attached Document';
    }
  }

  function hideActiveContext() {
    const bar = document.getElementById('active-context-bar');
    if (bar) bar.style.display = 'none';
  }

  // ── Session List ─────────────────────────────────────────────────────────

  async function loadSessions() {
    try {
      const chats = await API.get('/chats/');
      const list  = document.getElementById('session-list');
      if (!list) return;

      list.innerHTML = '';

      if (!chats || chats.length === 0) {
        list.innerHTML = '<div class="session-empty">No chats yet. Start a conversation!</div>';
        return;
      }

      chats.forEach(chat => {
        const item = document.createElement('div');
        item.className = 'session-item' + (chat.id === currentChatId ? ' active' : '');
        item.dataset.id = chat.id;
        item.innerHTML = `
          <span class="session-item-icon">💬</span>
          <span class="session-item-title">${escHtml(chat.title)}</span>
        `;
        item.addEventListener('click', () => openChat(chat.id));
        list.appendChild(item);
      });
    } catch (e) {
      console.error('loadSessions error', e);
    }
  }

  function setActiveSession(id) {
    document.querySelectorAll('.session-item').forEach(el => {
      el.classList.toggle('active', parseInt(el.dataset.id) === id);
    });
  }

  // ── Open Chat ─────────────────────────────────────────────────────────────

  async function openChat(id) {
    currentChatId = id;
    setActiveSession(id);
    clearDocPill();

    try {
      const chat = await API.get(`/chats/${id}/`);
      renderMessages(chat.messages || []);
      
      if (chat.active_document) {
        showActiveContext(chat.active_document);
      } else {
        hideActiveContext();
      }
    } catch (e) {
      showToast('Failed to load chat.', 'error');
    }
  }

  function renderMessages(messages) {
    const container = getMessagesEl();
    if (!container) return;
    container.innerHTML = '';

    if (messages.length === 0) {
      showEmpty();
      return;
    }

    showMessages();
    messages.forEach(m => appendMessage(m.role, m.content, false));
    container.scrollTop = container.scrollHeight;
  }

  // ── Append Message ────────────────────────────────────────────────────────

  function appendMessage(role, content, scroll = true) {
    showMessages();

    const container = getMessagesEl();
    if (!container) return;

    const isAI   = role === 'assistant';
    const isUser = role === 'user';

    const row    = document.createElement('div');
    row.className = `message-row ${isAI ? 'ai' : 'user'}`;

    // Avatar
    const avatar = document.createElement('div');
    avatar.className = `message-avatar ${isAI ? 'ai' : 'user'}`;
    avatar.innerHTML = isAI
      ? `<svg viewBox="0 0 40 40" fill="none" width="16" height="16"><circle cx="20" cy="12" r="4" fill="#00E5A3"/><path d="M20 19C12 14 4 17 4 17V33C12 31 18 29 20 34C22 29 28 31 36 33V17C36 17 28 14 20 19Z" fill="#00E5A3" opacity="0.85"/></svg>`
      : '👤';

    // Bubble
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';

    if (isAI && window.marked) {
      bubble.innerHTML = marked.parse(content);
      // Code copy buttons
      bubble.querySelectorAll('pre code').forEach(block => {
        if (window.hljs) hljs.highlightElement(block);
        const btn = document.createElement('button');
        btn.className   = 'copy-code-btn';
        btn.textContent = 'Copy';
        btn.addEventListener('click', () => {
          navigator.clipboard.writeText(block.textContent).then(() => {
            btn.textContent = 'Copied!';
            setTimeout(() => (btn.textContent = 'Copy'), 1800);
          });
        });
        block.parentElement.style.position = 'relative';
        block.parentElement.appendChild(btn);
      });
    } else {
      bubble.textContent = content;
    }

    if (isAI) {
      row.appendChild(avatar);
      row.appendChild(bubble);
    } else {
      row.appendChild(bubble);
      row.appendChild(avatar);
    }

    container.appendChild(row);
    if (scroll) container.scrollTop = container.scrollHeight;
  }

  // ── Typing Indicator ──────────────────────────────────────────────────────

  function showTyping() {
    showMessages();
    const container = getMessagesEl();
    if (!container) return;

    const row = document.createElement('div');
    row.className = 'message-row ai';
    row.id = 'typing-row';
    row.innerHTML = `
      <div class="message-avatar ai">
        <svg viewBox="0 0 40 40" fill="none" width="16" height="16">
          <circle cx="20" cy="12" r="4" fill="#00E5A3"/>
          <path d="M20 19C12 14 4 17 4 17V33C12 31 18 29 20 34C22 29 28 31 36 33V17C36 17 28 14 20 19Z" fill="#00E5A3" opacity="0.85"/>
        </svg>
      </div>
      <div class="message-bubble">
        <div class="typing-indicator">
          <div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>
        </div>
      </div>`;
    container.appendChild(row);
    container.scrollTop = container.scrollHeight;
  }

  function removeTyping() {
    document.getElementById('typing-row')?.remove();
  }

  // ── Send Message ──────────────────────────────────────────────────────────

  async function sendMessage(text) {
    if (!text.trim() || isWaiting) return;
    isWaiting = true;

    const submitBtn = document.getElementById('prompt-submit');
    if (submitBtn) submitBtn.disabled = true;

    // Lazy-create chat if none active
    if (!currentChatId) {
      try {
        const chat = await API.post('/chats/', {
          title: text.substring(0, 55) + (text.length > 55 ? '…' : ''),
        });
        currentChatId = chat.id;
        await loadSessions();         // Refresh list so new chat appears
        setActiveSession(currentChatId);
      } catch (e) {
        showToast('Failed to create chat session.', 'error');
        isWaiting = false;
        if (submitBtn) submitBtn.disabled = false;
        return;
      }
    }

    appendMessage('user', text);
    showTyping();

    try {
      // If we have a staged file, upload it first
      if (stagedFile) {
        const formData = new FormData();
        formData.append('file', stagedFile);
        formData.append('title', stagedFile.name.replace(/\.[^.]+$/, ''));
        formData.append('chat_id', currentChatId);

        const doc = await API.post('/documents/', formData);
        currentDocId = doc.document_id || doc.id;
        
        // Show active context pill and clear input pill
        showActiveContext({ id: currentDocId, title: stagedFile.name });
        stagedFile = null;
        clearDocPill();
      }

      const body = { content: text };

      const data = await API.post(`/chats/${currentChatId}/message/`, body);
      removeTyping();
      // Handle the robust response payload which contains "content" or "assistant_message"
      const content = data.content || data.assistant_message?.content;
      appendMessage('assistant', content);

      // Refresh chat list to update title after first message
      await loadSessions();
      setActiveSession(currentChatId);
    } catch (e) {
      removeTyping();
      const errMsg = e?.data?.details || e?.data?.error || 'Failed to get AI response. Check your API key in .env.';
      appendMessage('assistant', `⚠️ **Error:** ${errMsg}`);
    } finally {
      isWaiting = false;
      if (submitBtn) submitBtn.disabled = false;
    }
  }

  // ── New Chat ──────────────────────────────────────────────────────────────

  function startNewChat() {
    currentChatId = null;
    clearDocPill();
    hideActiveContext();
    setActiveSession(-1);   // Deactivate all
    showEmpty();
    const inp = document.getElementById('prompt-input');
    if (inp) { inp.value = ''; inp.style.height = 'auto'; inp.focus(); }
  }

  // ── Document Attachment (RAG) ─────────────────────────────────────────────

  function clearDocPill() {
    currentDocId = null;
    stagedFile = null;
    const pill = document.getElementById('doc-pill');
    if (pill) pill.style.display = 'none';
    const inp = document.getElementById('pdf-file-input');
    if (inp) inp.value = '';
  }

  async function handleFileSelect(file) {
    if (!file) return;

    // Stage the file
    stagedFile = file;

    // Show in the input pill
    const pill     = document.getElementById('doc-pill');
    const pillName = document.getElementById('doc-pill-name');
    if (pill && pillName) {
      pill.style.display = 'flex';
      pillName.textContent = file.name;
      pillName.style.color = 'var(--text-primary)';
    }
  }

  return {
    loadSessions,
    openChat,
    sendMessage,
    startNewChat,
    handleFileSelect,
    clearDocPill,
    hideActiveContext,
  };
})();


/* ═══════════════════════════════════════════════════════════════════════════
   Utility
   ═══════════════════════════════════════════════════════════════════════════ */
function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}


/* ═══════════════════════════════════════════════════════════════════════════
   App Init — called after successful login
   ═══════════════════════════════════════════════════════════════════════════ */
function initApp(user) {
  // Populate sidebar user info
  const u = user || Auth.getUser();
  if (u) {
    const initials = ((u.first_name?.[0] || '') + (u.last_name?.[0] || '') || u.email?.[0] || 'U').toUpperCase();
    const el = document.getElementById('sidebar-avatar');
    if (el) el.textContent = initials;

    const nameEl  = document.getElementById('sidebar-name');
    const emailEl = document.getElementById('sidebar-email');
    if (nameEl)  nameEl.textContent  = [u.first_name, u.last_name].filter(Boolean).join(' ') || u.email;
    if (emailEl) emailEl.textContent = u.email || '';
  }

  // Sign out
  document.getElementById('btn-logout')?.addEventListener('click', Auth.logout);

  // New Chat button
  document.getElementById('btn-new-chat')?.addEventListener('click', ChatModule.startNewChat);

  // PDF File Input
  const fileInput = document.getElementById('pdf-file-input');
  fileInput?.addEventListener('change', () => {
    const file = fileInput.files[0];
    if (file) ChatModule.handleFileSelect(file);
  });

  // Remove doc pill
  document.getElementById('doc-pill-remove')?.addEventListener('click', () => {
    ChatModule.clearDocPill();
  });

  // Remove active context
  document.getElementById('active-context-remove')?.addEventListener('click', () => {
    ChatModule.hideActiveContext();
  });

  // Prompt submit button
  document.getElementById('prompt-submit')?.addEventListener('click', submitMessage);

  // Textarea: auto-resize + Enter to submit
  const textarea = document.getElementById('prompt-input');
  if (textarea) {
    textarea.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        submitMessage();
      }
    });
    textarea.addEventListener('input', () => {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 160) + 'px';
    });
  }

  // Suggestion pills
  document.querySelectorAll('.suggestion-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      const promptText = pill.dataset.prompt;
      if (textarea) {
        textarea.value = promptText;
        textarea.focus();
      }
      submitMessage();
    });
  });

  // Load chat history
  ChatModule.loadSessions();
}

function submitMessage() {
  const textarea = document.getElementById('prompt-input');
  if (!textarea) return;
  const text = textarea.value.trim();
  if (!text) return;
  textarea.value = '';
  textarea.style.height = 'auto';
  ChatModule.sendMessage(text);
}


/* ═══════════════════════════════════════════════════════════════════════════
   Bootstrap
   ═══════════════════════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  if (Auth.isLoggedIn()) {
    document.getElementById('auth-overlay')?.remove();
    initApp();
  } else {
    setupAuthUI();
  }

  // ── Sidebar Toggle Logic ──
  const appContainer = document.getElementById("app");
  const toggleBtn = document.getElementById("btn-toggle-sidebar");

  // Load saved preference from local storage
  const isCollapsed = localStorage.getItem("sidebarCollapsed") === "true";
  if (isCollapsed && appContainer) {
      appContainer.classList.add("sidebar-collapsed");
  }

  if (toggleBtn && appContainer) {
      toggleBtn.addEventListener("click", () => {
          appContainer.classList.toggle("sidebar-collapsed");
          
          // Save state preference
          const nowCollapsed = appContainer.classList.contains("sidebar-collapsed");
          localStorage.setItem("sidebarCollapsed", nowCollapsed);
      });
  }
});
