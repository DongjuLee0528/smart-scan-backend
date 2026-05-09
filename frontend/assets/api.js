/*!
 * SmartScan Hub — Shared API Client (vanilla JS)
 *
 * Usage example:
 *   const res = await smartscanApi.login('user@example.com', 'pw');
 *   smartscanApi.setTokens(res.data);
 *   await smartscanApi.linkKakao(kakaoLinkJwt);
 *
 * If deployment origin differs from API, declare in HTML: <script>window.SMARTSCAN_API_BASE='https://api.example.com'</script>
 */
(function () {
  "use strict";

  // Auto-detect API base URL based on environment and configuration
  function detectApiBase() {
    if (typeof window !== "undefined" && window.SMARTSCAN_API_BASE) {
      return window.SMARTSCAN_API_BASE.replace(/\/$/, "");
    }
    // Local dev: when opening static HTML via file:// or localhost:* → uvicorn(:8000)
    if (typeof location !== "undefined") {
      const host = location.hostname;
      if (!host || host === "localhost" || host === "127.0.0.1") {
        return "http://localhost:8000";
      }
      return location.origin;
    }
    return "";
  }

  const API_BASE = detectApiBase();
  const STORAGE_KEYS = {
    ACCESS: "smartscan.access_token",
    REFRESH: "smartscan.refresh_token",
    USER: "smartscan.user",
  };

  function getAccessToken() {
    return localStorage.getItem(STORAGE_KEYS.ACCESS);
  }

  function getRefreshToken() {
    return localStorage.getItem(STORAGE_KEYS.REFRESH);
  }

  function getUser() {
    const raw = localStorage.getItem(STORAGE_KEYS.USER);
    return raw ? JSON.parse(raw) : null;
  }

  // Store authentication tokens and user info in localStorage
  function setTokens(data) {
    if (!data) return;
    if (data.access_token) localStorage.setItem(STORAGE_KEYS.ACCESS, data.access_token);
    if (data.refresh_token) localStorage.setItem(STORAGE_KEYS.REFRESH, data.refresh_token);
    const user = {
      user_id: data.user_id,
      kakao_user_id: data.kakao_user_id,
      email: data.email,
      name: data.name,
    };
    localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user));
  }

  function clearTokens() {
    localStorage.removeItem(STORAGE_KEYS.ACCESS);
    localStorage.removeItem(STORAGE_KEYS.REFRESH);
    localStorage.removeItem(STORAGE_KEYS.USER);
  }

  function isLoggedIn() {
    return !!getAccessToken();
  }

  // Generate UUID v4 with crypto API fallback to Math.random
  function uuidV4() {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
      return crypto.randomUUID();
    }
    return "xxxxxxxxxxxx4xxxyxxxxxxxxxxxxxxx".replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  // Serialize with shared Promise to ensure refresh runs only once even when multiple requests receive 401.
  let _refreshInFlight = null;

  async function _performRefresh() {
    const refresh = getRefreshToken();
    if (!refresh) throw new Error("no refresh token");
    const res = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) {
      const err = new Error("refresh failed");
      err.status = res.status;
      throw err;
    }
    const payload = await res.json();
    if (!payload || !payload.data) {
      throw new Error("refresh response missing data");
    }
    setTokens(payload.data);
    return payload.data.access_token;
  }

  function _onAuthFailure() {
    clearTokens();
    if (typeof window !== "undefined" && window.location) {
      // Prevent loop if already on login/signup page.
      const p = window.location.pathname || "";
      const onAuthPage = /\/(index\.html|signup\.html|kakao-link\.html)?$/i.test(p);
      if (!onAuthPage) {
        window.location.href = "/index.html";
      }
    }
  }

  async function _rawFetch(path, options, authToken) {
    const headers = Object.assign(
      { "Content-Type": "application/json" },
      options.headers || {}
    );
    if (authToken) headers.Authorization = `Bearer ${authToken}`;

    let res;
    try {
      res = await fetch(`${API_BASE}${path}`, {
        method: options.method || "GET",
        headers,
        body: options.body ? JSON.stringify(options.body) : undefined,
      });
    } catch (networkErr) {
      const err = new Error("Network error: Cannot connect to server.");
      err.cause = networkErr;
      throw err;
    }

    let payload = null;
    const text = await res.text();
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch {
        payload = { message: text };
      }
    }
    return { res, payload };
  }

  /**
   * Low-level fetch wrapper. Unpacks server response schema { success, message, data }.
   * Throws Error on failure (includes err.status, err.body properties).
   *
   * When auth request receives 401, automatically reissues access token with refresh token
   * then retries original request once. If refresh also fails, clears local tokens and redirects to login page.
   */
  async function apiFetch(path, options = {}) {
    // Flag branching to prevent recursive calls when refresh endpoint itself receives 401.
    const isRefreshCall = path === "/api/auth/refresh";

    let token = null;
    if (options.auth) {
      token = getAccessToken();
      if (!token) {
        const err = new Error("Not authenticated");
        err.status = 401;
        throw err;
      }
    }

    let { res, payload } = await _rawFetch(path, options, token);

    // If 401 and auth request but not refresh itself → refresh token and retry once.
    if (
      res.status === 401 &&
      options.auth &&
      !isRefreshCall &&
      !options._retried
    ) {
      try {
        if (!_refreshInFlight) {
          _refreshInFlight = _performRefresh().finally(() => {
            _refreshInFlight = null;
          });
        }
        const newToken = await _refreshInFlight;
        const retry = await _rawFetch(
          path,
          Object.assign({}, options, { _retried: true }),
          newToken
        );
        res = retry.res;
        payload = retry.payload;
      } catch (refreshErr) {
        _onAuthFailure();
        const err = new Error("Session has expired. Please log in again.");
        err.status = 401;
        err.cause = refreshErr;
        throw err;
      }
    }

    if (!res.ok || (payload && payload.success === false)) {
      const err = new Error(
        (payload && (payload.message || payload.detail)) ||
          `Request failed with status ${res.status}`
      );
      err.status = res.status;
      err.body = payload;
      throw err;
    }

    return payload;
  }

  // ---------- High-level endpoint wrappers ----------

  async function login(email, password) {
    const res = await apiFetch("/api/auth/login", {
      method: "POST",
      body: { email, password },
    });
    if (res && res.data) setTokens(res.data);
    return res;
  }

  async function register({
    name,
    email,
    password,
    phone = null,
    age = null,
    family_name = null,
    kakao_user_id = null,
  }) {
    const uid = kakao_user_id || `pending_${uuidV4()}`;
    return apiFetch("/api/auth/register", {
      method: "POST",
      body: {
        kakao_user_id: uid,
        name,
        email,
        password,
        phone,
        age,
        family_name,
      },
    });
  }

  async function logout() {
    const refresh = getRefreshToken();
    if (!refresh) {
      clearTokens();
      return;
    }
    try {
      await apiFetch("/api/auth/logout", {
        method: "POST",
        auth: true,
        body: { refresh_token: refresh },
      });
    } finally {
      clearTokens();
    }
  }

  async function linkKakao(token) {
    return apiFetch("/api/auth/link-kakao", {
      method: "POST",
      auth: true,
      body: { token },
    });
  }

  async function sendVerificationEmail(email) {
    return apiFetch("/api/auth/send-verification-email", {
      method: "POST",
      body: { email },
    });
  }

  async function verifyEmail(email, code) {
    return apiFetch("/api/auth/verify-email", {
      method: "POST",
      body: { email, code },
    });
  }

  /** Page guard: Redirect to login.html if not logged in (preserves current URL as redirect parameter). */
  function requireLogin() {
    if (!isLoggedIn()) {
      const redirect = encodeURIComponent(location.pathname + location.search);
      location.replace(`login.html?redirect=${redirect}`);
      return false;
    }
    return true;
  }

  // ---------- Devices ----------
  const registerDevice = (serial_number) =>
    apiFetch("/api/devices/register", { method: "POST", auth: true, body: { serial_number } });
  const getMyDevice = () => apiFetch("/api/devices/me", { auth: true });
  const unlinkDevice = () => apiFetch("/api/devices/me", { method: "DELETE", auth: true });

  // ---------- Family members ----------
  const addFamilyMember = (body) =>
    apiFetch("/api/families/members", { method: "POST", auth: true, body });
  const getFamilyMembers = () => apiFetch("/api/families/members", { auth: true });
  const deleteFamilyMember = (id) =>
    apiFetch(`/api/families/members/${id}`, { method: "DELETE", auth: true });

  // ---------- Items ----------
  const getItems = () => apiFetch("/api/items", { auth: true });
  const addItem = (body) => apiFetch("/api/items", { method: "POST", auth: true, body });
  const updateItem = (id, body) =>
    apiFetch(`/api/items/${id}`, { method: "PATCH", auth: true, body });
  const deleteItem = (id) => apiFetch(`/api/items/${id}`, { method: "DELETE", auth: true });
  // A-full: Link label to pending item (chatbot name only added) → activate
  const bindItemLabel = (id, label_id) =>
    apiFetch(`/api/items/${id}/bind`, { method: "PATCH", auth: true, body: { label_id } });

  // ---------- Labels ----------
  const getAvailableLabels = () => apiFetch("/api/labels/available", { auth: true });

  // ---------- Tags ----------
  const createTag = (body) => apiFetch("/api/tags", { method: "POST", auth: true, body });
  const getTags = () => apiFetch("/api/tags", { auth: true });
  const updateTag = (id, body) =>
    apiFetch(`/api/tags/${id}`, { method: "PATCH", auth: true, body });
  const deleteTag = (id) => apiFetch(`/api/tags/${id}`, { method: "DELETE", auth: true });

  // ---------- Monitoring ----------
  const getDashboard = () => apiFetch("/api/monitoring/dashboard", { auth: true });
  const getMyTags = () => apiFetch("/api/monitoring/my-tags", { auth: true });
  const getMemberTags = (memberId) =>
    apiFetch(`/api/monitoring/members/${memberId}/tags`, { auth: true });

  // ---------- Notifications ----------
  const sendNotification = (userId, body) =>
    apiFetch(`/api/notifications/send/${userId}`, { method: "POST", auth: true, body });
  const getMyNotifications = () => apiFetch("/api/notifications", { auth: true });
  const markNotificationAsRead = (id) =>
    apiFetch(`/api/notifications/${id}/read`, { method: "PATCH", auth: true });

  // ---------- Scan logs ----------
  const createScanLog = (body) =>
    apiFetch("/api/scan-logs", { method: "POST", auth: true, body });

  // ---------- Family Invitations ----------

  /** GET request without authentication (for public endpoints like invitation token lookup). */
  async function _getPublic(path) {
    const headers = { "Content-Type": "application/json" };
    let res;
    try {
      res = await fetch(`${API_BASE}${path}`, { method: "GET", headers });
    } catch (networkErr) {
      const err = new Error("Network error: Cannot connect to server.");
      err.cause = networkErr;
      throw err;
    }
    let payload = null;
    const text = await res.text();
    if (text) {
      try { payload = JSON.parse(text); } catch { payload = { message: text }; }
    }
    if (!res.ok || (payload && payload.success === false)) {
      const err = new Error(
        (payload && (payload.message || payload.detail)) ||
          `Request failed with status ${res.status}`
      );
      err.status = res.status;
      err.body = payload;
      throw err;
    }
    return payload;
  }

  const createInvitation = (body) =>
    apiFetch("/api/family-invitations", { method: "POST", auth: true, body });
  const listInvitations = () =>
    apiFetch("/api/family-invitations", { auth: true });
  const cancelInvitation = (id) =>
    apiFetch(`/api/family-invitations/${id}`, { method: "DELETE", auth: true });
  const getInvitationByToken = (token) =>
    _getPublic(`/api/family-invitations/by-token/${encodeURIComponent(token)}`);
  const acceptInvitation = (token) =>
    apiFetch(`/api/family-invitations/${encodeURIComponent(token)}/accept`, { method: "POST", auth: true, body: {} });
  const declineInvitation = (token) =>
    apiFetch(`/api/family-invitations/${encodeURIComponent(token)}/decline`, { method: "POST", auth: true, body: {} });

  window.smartscanApi = {
    API_BASE,
    getAccessToken,
    getRefreshToken,
    getUser,
    setTokens,
    clearTokens,
    isLoggedIn,
    requireLogin,
    apiFetch,
    login,
    register,
    logout,
    linkKakao,
    sendVerificationEmail,
    verifyEmail,
    // devices
    registerDevice,
    getMyDevice,
    unlinkDevice,
    // family
    addFamilyMember,
    getFamilyMembers,
    deleteFamilyMember,
    // items
    getItems,
    addItem,
    updateItem,
    deleteItem,
    bindItemLabel,
    // labels
    getAvailableLabels,
    // tags
    createTag,
    getTags,
    updateTag,
    deleteTag,
    // monitoring
    getDashboard,
    getMyTags,
    getMemberTags,
    // notifications
    sendNotification,
    getMyNotifications,
    markNotificationAsRead,
    // scan logs
    createScanLog,
    // family invitations
    createInvitation,
    listInvitations,
    cancelInvitation,
    getInvitationByToken,
    acceptInvitation,
    declineInvitation,
  };
})();
