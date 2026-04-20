/*!
 * SmartScan Hub — 공용 API 클라이언트 (vanilla JS)
 *
 * 사용 예:
 *   const res = await smartscanApi.login('user@example.com', 'pw');
 *   smartscanApi.setTokens(res.data);
 *   await smartscanApi.linkKakao(kakaoLinkJwt);
 *
 * 배포 오리진이 API와 다르면 HTML에서 <script>window.SMARTSCAN_API_BASE='https://api.example.com'</script> 선언.
 */
(function () {
  "use strict";

  function detectApiBase() {
    if (typeof window !== "undefined" && window.SMARTSCAN_API_BASE) {
      return window.SMARTSCAN_API_BASE.replace(/\/$/, "");
    }
    // 로컬 dev: 정적 HTML을 file:// 또는 localhost:* 로 열 때 → uvicorn(:8000)
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

  // 동시에 여러 요청이 401 을 받아도 refresh 는 한 번만 돌도록 공유 Promise 로 직렬화.
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
      // 이미 로그인/회원가입 페이지에 있으면 루프 방지.
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
      const err = new Error("네트워크 오류: 서버에 접속할 수 없습니다.");
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
   * 저수준 fetch 래퍼. 서버 응답 스키마 { success, message, data } 를 언패킹한다.
   * 실패 시 Error throw (err.status, err.body 속성 포함).
   *
   * auth 요청이 401 을 받으면 refresh token 으로 access token 을 자동 재발급한 뒤
   * 원요청을 1 회 재시도한다. refresh 도 실패하면 로컬 토큰을 비우고 로그인 페이지로 이동.
   */
  async function apiFetch(path, options = {}) {
    // refresh 엔드포인트 자체가 401 받을 때 재귀 호출하지 않도록 플래그 분기.
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

    // 401 이면서 auth 요청이고 refresh 자체가 아닌 경우 → 토큰 갱신 후 1회 재시도.
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
        const err = new Error("세션이 만료되었습니다. 다시 로그인해 주세요.");
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

  // ---------- 고수준 엔드포인트 래퍼 ----------

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

  /** 페이지 가드: 미로그인 시 login.html로 리다이렉트 (현재 URL을 redirect 파라미터로 보존). */
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
  // A-full: pending 아이템(챗봇 이름만 추가)에 라벨 연결 → 활성화
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

  /** 인증 없이 GET 요청 (초대 토큰 조회 등 public 엔드포인트용). */
  async function _getPublic(path) {
    const headers = { "Content-Type": "application/json" };
    let res;
    try {
      res = await fetch(`${API_BASE}${path}`, { method: "GET", headers });
    } catch (networkErr) {
      const err = new Error("네트워크 오류: 서버에 접속할 수 없습니다.");
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
