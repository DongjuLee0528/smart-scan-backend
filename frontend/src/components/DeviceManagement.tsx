/**
 * RFID 디바이스 관리 컴포넌트
 *
 * Smart Scan 시스템에 연결된 RFID 리더기 디바이스들을 등록하고 관리하는 페이지입니다.
 * 새로운 디바이스 등록, 기존 디바이스 목록 조회, 디바이스 삭제 기능을 제공합니다.
 */

import { useState } from "react";

// RFID 디바이스 정보 인터페이스
interface Device {
  id: string;          // 고유 식별자
  name: string;        // 사용자 정의 디바이스 이름 (예: "현관 리더기")
  serial: string;      // 하드웨어 시리얼 번호
  status: "활성" | "비활성";  // 디바이스 동작 상태
  registeredAt: string;     // 등록 날짜
}

// 초기 등록된 디바이스 데이터 (임시 데이터)
const initialDevices: Device[] = [
  { id: "1", name: "현관 리더기", serial: "SH-0001", status: "활성", registeredAt: "2023.10.27" },
];

/**
 * 디바이스 관리 메인 컴포넌트
 *
 * 디바이스 등록 폼과 기존 등록된 디바이스 목록을 테이블 형태로 표시합니다.
 * 실제 환경에서는 백엔드 API와 연동하여 데이터를 관리해야 합니다.
 */
export default function DeviceManagement() {
  const [devices, setDevices] = useState<Device[]>(initialDevices);  // 디바이스 목록 상태
  const [serial, setSerial] = useState("SH-0001");                   // 입력 중인 시리얼 번호
  const [deviceName, setDeviceName] = useState("현관 리더기");        // 입력 중인 디바이스 이름

  /**
   * 새 디바이스 등록 핸들러
   *
   * 시리얼 번호와 디바이스 이름을 검증한 후 새로운 디바이스를 목록에 추가합니다.
   */
  const handleRegister = () => {
    if (!serial || !deviceName) return;
    const newDevice: Device = {
      id: Date.now().toString(),
      name: deviceName,
      serial,
      status: "활성",
      registeredAt: new Date().toLocaleDateString("ko-KR", {
        year: "numeric", month: "2-digit", day: "2-digit",
      }).replace(/\. /g, ".").replace(".", "").slice(0, -1),
    };
    setDevices([...devices, newDevice]);
    setSerial("");
    setDeviceName("");
  };

  return (
    <div>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: "#111827", marginBottom: 4 }}>기기 관리</h1>
      <p style={{ color: "#6b7280", fontSize: 14, marginBottom: 28 }}>집안에 설치된 RFID 리더기를 등록하고 관리하세요.</p>

      {/* 기기 등록 카드 */}
      <div style={{
        background: "#fff",
        border: "1px solid #e5e7eb",
        borderRadius: 12,
        padding: "24px",
        marginBottom: 24,
      }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, color: "#111827", marginBottom: 4 }}>기기 등록</h2>
        <p style={{ color: "#6b7280", fontSize: 13, marginBottom: 20 }}>새로운 SmartScan Hub 리더기를 시스템에 추가합니다.</p>

        <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
          <div style={{ flex: 1 }}>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#374151", marginBottom: 6 }}>
              시리얼 번호
            </label>
            <input
              value={serial}
              onChange={e => setSerial(e.target.value)}
              placeholder="SH-0001"
              style={{
                width: "100%",
                padding: "10px 14px",
                border: "1px solid #d1d5db",
                borderRadius: 8,
                fontSize: 14,
                outline: "none",
                boxSizing: "border-box",
              }}
            />
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#374151", marginBottom: 6 }}>
              기기 이름
            </label>
            <input
              value={deviceName}
              onChange={e => setDeviceName(e.target.value)}
              placeholder="현관 리더기"
              style={{
                width: "100%",
                padding: "10px 14px",
                border: "1px solid #d1d5db",
                borderRadius: 8,
                fontSize: 14,
                outline: "none",
                boxSizing: "border-box",
              }}
            />
          </div>
          <button
            onClick={handleRegister}
            style={{
              padding: "10px 20px",
              background: "#2563eb",
              color: "#fff",
              border: "none",
              borderRadius: 8,
              fontSize: 14,
              fontWeight: 600,
              cursor: "pointer",
              whiteSpace: "nowrap",
              height: 42,
            }}
          >
            + 등록
          </button>
        </div>
      </div>

      {/* 등록된 기기 목록 카드 */}
      <div style={{
        background: "#fff",
        border: "1px solid #e5e7eb",
        borderRadius: 12,
        padding: "24px",
      }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, color: "#111827", marginBottom: 20 }}>등록된 기기 목록</h2>

        {/* 테이블 헤더 */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "2fr 2fr 1.5fr 1.5fr 1fr",
          padding: "8px 0",
          borderBottom: "1px solid #e5e7eb",
          marginBottom: 8,
        }}>
          {["기기 이름", "시리얼 번호", "상태", "등록일", "관리"].map(col => (
            <span key={col} style={{ fontSize: 13, color: "#6b7280", fontWeight: 500 }}>{col}</span>
          ))}
        </div>

        {/* 기기 행 */}
        {devices.map(device => (
          <div
            key={device.id}
            style={{
              display: "grid",
              gridTemplateColumns: "2fr 2fr 1.5fr 1.5fr 1fr",
              alignItems: "center",
              padding: "14px 0",
              borderBottom: "1px solid #f3f4f6",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{
                width: 28, height: 28, background: "#dbeafe",
                borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center",
                color: "#2563eb", fontSize: 14,
              }}>☐</div>
              <span style={{ fontSize: 14, color: "#111827", fontWeight: 500 }}>{device.name}</span>
            </div>
            <span style={{ fontSize: 14, color: "#374151" }}>{device.serial}</span>
            <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{
                width: 8, height: 8, borderRadius: "50%",
                background: device.status === "활성" ? "#10b981" : "#9ca3af",
                display: "inline-block",
              }} />
              <span style={{ fontSize: 13, color: device.status === "활성" ? "#10b981" : "#9ca3af", fontWeight: 500 }}>
                {device.status}
              </span>
            </span>
            <span style={{ fontSize: 13, color: "#6b7280" }}>{device.registeredAt}</span>
            <button
              onClick={() => setDevices(devices.filter(d => d.id !== device.id))}
              style={{
                fontSize: 12, color: "#ef4444", background: "none",
                border: "1px solid #fca5a5", borderRadius: 6,
                padding: "4px 10px", cursor: "pointer",
              }}
            >
              삭제
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}