/**
 * Smart Scan Hub 메인 애플리케이션 컴포넌트
 *
 * React 기반의 SPA로 Smart Scan 시스템의 웹 대시보드를 제공합니다.
 * 사이드바 네비게이션과 페이지별 컨텐츠 렌더링을 담당합니다.
 */

import { useState } from "react";
import DeviceManagement from "./components/DeviceManagement";

// 애플리케이션 페이지 타입 정의
type Page = "대시보드" | "기기 관리" | "소지품 관리" | "구성원 관리" | "알림" | "설정";

// 사이드바 네비게이션 메뉴 아이템 정의
const navItems: { label: Page; icon: string }[] = [
  { label: "대시보드", icon: "⊞" },
  { label: "기기 관리", icon: "☐" },
  { label: "소지품 관리", icon: "◎" },
  { label: "구성원 관리", icon: "👤" },
  { label: "알림", icon: "🔔" },
  { label: "설정", icon: "⚙" },
];

/**
 * 메인 App 컴포넌트
 *
 * 좌측 사이드바와 우측 메인 컨텐츠 영역으로 구성된 레이아웃을 제공합니다.
 * 현재는 기기 관리 페이지만 구현되어 있으며, 다른 페이지들은 placeholder로 표시됩니다.
 */
export default function App() {
  const [activePage, setActivePage] = useState<Page>("기기 관리");

  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: "'Pretendard', 'Apple SD Gothic Neo', sans-serif", background: "#f8f9fa" }}>
      {/* Sidebar */}
      <aside style={{
        width: 180,
        background: "#fff",
        borderRight: "1px solid #e5e7eb",
        display: "flex",
        flexDirection: "column",
        padding: "16px 0",
      }}>
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 20px 24px" }}>
          <div style={{
            width: 28, height: 28, borderRadius: "50%",
            background: "#3b82f6", display: "flex", alignItems: "center", justifyContent: "center",
            color: "#fff", fontSize: 13, fontWeight: 700,
          }}>S</div>
          <span style={{ fontWeight: 700, fontSize: 15, color: "#111827" }}>SmartScan Hub</span>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1 }}>
          {navItems.map(({ label, icon }) => (
            <button
              key={label}
              onClick={() => setActivePage(label)}
              style={{
                width: "100%",
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "10px 20px",
                border: "none",
                background: activePage === label ? "#eff6ff" : "transparent",
                color: activePage === label ? "#2563eb" : "#6b7280",
                fontWeight: activePage === label ? 600 : 400,
                fontSize: 14,
                cursor: "pointer",
                textAlign: "left",
                borderRadius: activePage === label ? "0 8px 8px 0" : 0,
                position: "relative",
              }}
            >
              <span>{icon}</span>
              {label}
              {label === "알림" && (
                <span style={{
                  marginLeft: "auto",
                  background: "#ef4444",
                  color: "#fff",
                  borderRadius: "50%",
                  width: 18, height: 18,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 11, fontWeight: 700,
                }}>3</span>
              )}
            </button>
          ))}
        </nav>

        {/* Logout */}
        <button style={{
          display: "flex", alignItems: "center", gap: 8,
          padding: "10px 20px", border: "none", background: "transparent",
          color: "#6b7280", fontSize: 14, cursor: "pointer",
        }}>
          ↩ 로그아웃
        </button>
      </aside>

      {/* Main */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        {/* Header */}
        <header style={{
          height: 56,
          background: "#fff",
          borderBottom: "1px solid #e5e7eb",
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-end",
          padding: "0 24px",
          gap: 12,
        }}>
          <span style={{ color: "#374151", fontSize: 14 }}>이준호네 가족</span>
          <button style={{ background: "none", border: "none", cursor: "pointer", color: "#6b7280", fontSize: 18 }}>☀</button>
          <div style={{
            width: 32, height: 32, borderRadius: "50%",
            background: "#3b82f6", color: "#fff",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontWeight: 700, fontSize: 14,
          }}>이</div>
        </header>

        {/* Page Content */}
        <main style={{ flex: 1, overflow: "auto", padding: "36px 48px" }}>
          {activePage === "기기 관리" && <DeviceManagement />}
          {activePage !== "기기 관리" && (
            <div style={{ color: "#9ca3af", fontSize: 16 }}>{activePage} 페이지</div>
          )}
        </main>
      </div>
    </div>
  );
}