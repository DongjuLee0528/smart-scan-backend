/*!
 * SmartScan Hub — 공용 레이아웃 헬퍼
 *
 * 모든 대시보드 페이지에서 공유하는 사이드바 렌더링 + 로그인 가드 + 현재 사용자 정보 주입.
 *
 * 사용법 (각 페이지 head에서):
 *   <script src="assets/api.js"></script>
 *   <script src="assets/layout.js"></script>
 * body 안에:
 *   <aside id="sidebar-mount"></aside>
 *   ... 페이지 콘텐츠 ...
 *   <script>smartscanLayout.init({active: 'dashboard'});</script>
 */
(function () {
  "use strict";

  const NAV_ITEMS = [
    { key: "dashboard", label: "대시보드", href: "dashboard.html", icon: `<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>` },
    { key: "devices", label: "기기 관리", href: "devices.html", icon: `<rect width="14" height="20" x="5" y="2" rx="2" ry="2"/><path d="M12 18h.01"/>` },
    { key: "items", label: "소지품 관리", href: "items.html", icon: `<path d="M12 2H2v10l9.29 9.29c.94.94 2.48.94 3.42 0l6.58-6.58c.94-.94.94-2.48 0-3.42L12 2Z"/><path d="M7 7h.01"/>` },
    { key: "members", label: "구성원 관리", href: "members.html", icon: `<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>` },
    { key: "notifications", label: "알림", href: "notifications.html", icon: `<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>` },
    { key: "settings", label: "설정", href: "settings.html", icon: `<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>` },
  ];

  function navIcon(path) {
    return `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${path}</svg>`;
  }

  function renderSidebar(active, user, badgeCount) {
    const navHtml = NAV_ITEMS.map((item) => {
      const isActive = item.key === active;
      const cls = isActive
        ? "flex items-center gap-3 px-3 py-2.5 rounded-lg bg-[#034EA2]/10 text-[#034EA2] transition-colors"
        : "flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-600 hover:bg-slate-50 transition-colors";
      const badge = item.key === "notifications" && badgeCount > 0
        ? `<span class="ml-auto text-xs font-semibold bg-red-100 text-red-600 px-2 py-0.5 rounded-full">${badgeCount}</span>`
        : "";
      return `<a href="${item.href}" class="${cls}">${navIcon(item.icon)}<span class="font-medium text-sm">${item.label}</span>${badge}</a>`;
    }).join("");

    const name = user && user.name ? user.name : "사용자";
    const email = user && user.email ? user.email : "";
    const initial = name.charAt(0);

    return `
      <div class="h-16 flex items-center px-6 border-b border-slate-200">
        <div class="flex items-center gap-2 text-[#034EA2]">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/>
            <path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/>
            <circle cx="12" cy="12" r="3"/>
          </svg>
          <span class="text-xl font-bold tracking-tight">SmartScan Hub</span>
        </div>
      </div>
      <nav class="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
        ${navHtml}
      </nav>
      <div class="p-4 border-t border-slate-200">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-full bg-[#034EA2]/10 text-[#034EA2] flex items-center justify-center font-semibold text-sm shrink-0">${initial}</div>
          <div class="min-w-0 flex-1">
            <p class="text-sm font-semibold text-slate-800 truncate">${name}</p>
            <p class="text-xs text-slate-500 truncate">${email}</p>
          </div>
          <button id="logout-btn" class="p-1.5 rounded-md text-slate-400 hover:bg-slate-100 hover:text-slate-600" title="로그아웃">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/></svg>
          </button>
        </div>
      </div>
    `;
  }

  function bindLogout() {
    const btn = document.getElementById("logout-btn");
    if (!btn) return;
    btn.addEventListener("click", async () => {
      try {
        await smartscanApi.logout();
      } catch (_) {
        // ignore
      }
      location.replace("login.html");
    });
  }

  async function init(options) {
    const opts = options || {};
    if (!smartscanApi.requireLogin()) return;

    const user = smartscanApi.getUser();
    const mount = document.getElementById("sidebar-mount");

    // 미리 그린 뒤 알림 뱃지 업데이트
    if (mount) {
      mount.className = "w-64 bg-white border-r border-slate-200 flex-col hidden md:flex shrink-0";
      mount.innerHTML = renderSidebar(opts.active, user, 0);
      bindLogout();
    }

    // 알림 개수 비동기 갱신 (실패해도 무시)
    try {
      const res = await smartscanApi.getMyNotifications();
      const list = (res && res.data && res.data.notifications) || [];
      const unread = list.filter((n) => !n.is_read).length;
      if (mount && unread > 0) {
        mount.innerHTML = renderSidebar(opts.active, user, unread);
        bindLogout();
      }
    } catch (_) {
      // noop
    }
  }

  // 공용 유틸
  function escapeHtml(s) {
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatDateTime(iso) {
    if (!iso) return "-";
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    const now = new Date();
    const sameDay = d.toDateString() === now.toDateString();
    const yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);
    const isYesterday = d.toDateString() === yesterday.toDateString();
    const hh = String(d.getHours()).padStart(2, "0");
    const mm = String(d.getMinutes()).padStart(2, "0");
    if (sameDay) return `오늘 ${hh}:${mm}`;
    if (isYesterday) return `어제 ${hh}:${mm}`;
    return `${d.getMonth() + 1}/${d.getDate()} ${hh}:${mm}`;
  }

  function toast(message, type) {
    const existing = document.getElementById("smartscan-toast");
    if (existing) existing.remove();
    const el = document.createElement("div");
    el.id = "smartscan-toast";
    const color = type === "error"
      ? "bg-red-600"
      : type === "success"
        ? "bg-emerald-600"
        : "bg-slate-800";
    el.className = `fixed top-4 right-4 z-50 px-4 py-2.5 rounded-lg shadow-lg text-white text-sm ${color}`;
    el.textContent = message;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 3500);
  }

  window.smartscanLayout = { init, escapeHtml, formatDateTime, toast };
})();
