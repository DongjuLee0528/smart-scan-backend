/**
 * Smart Scan Hub main application component
 *
 * Provides web dashboard for Smart Scan system as React-based SPA.
 * Handles sidebar navigation and page-specific content rendering.
 */

import { useState } from "react";
import DeviceManagement from "./components/DeviceManagement";

// Application page type definition
type Page = "대시보드" | "기기 관리" | "소지품 관리" | "구성원 관리" | "알림" | "설정";

// Sidebar navigation menu item definition
const navItems: { label: Page; icon: string }[] = [
  { label: "대시보드", icon: "Dashboard" },
  { label: "기기 관리", icon: "Device" },
  { label: "소지품 관리", icon: "Item" },
  { label: "구성원 관리", icon: "User" },
  { label: "알림", icon: "Notification" },
  { label: "설정", icon: "Settings" },
];

/**
 * Main App component
 *
 * Provides layout composed of left sidebar and right main content area.
 * Currently only device management page is implemented, other pages are displayed as placeholders.
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
          ↩ Logout
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
          <span style={{ color: "#374151", fontSize: 14 }}>Lee Jun Ho's Family</span>
          <button style={{ background: "none", border: "none", cursor: "pointer", color: "#6b7280", fontSize: 18 }}>Theme</button>
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
            <div style={{ color: "#9ca3af", fontSize: 16 }}>{activePage} Page</div>
          )}
        </main>
      </div>
    </div>
  );
}