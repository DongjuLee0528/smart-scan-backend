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

  /**
   * 저수준 fetch 래퍼. 서버 응답 스키마 { success, message, data } 를 언패킹한다.
   * 실패 시 Error throw (err.status, err.body 속성 포함).
   */
  async function apiFetch(path, options = {}) {
    const headers = Object.assign(
      { "Content-Type": "application/json" },
      options.headers || {}
    );

    if (options.auth) {
      const token = getAccessToken();
      if (!token) {
        const err = new Error("Not authenticated");
        err.status = 401;
        throw err;
      }
      headers.Authorization = `Bearer ${token}`;
    }

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
  };
})();
