"""
FI-805F UHF RFID 리더기 드라이버

프레임 구조 (UHF RFID 공통 프로토콜):
  [0xBB] [Type] [Cmd] [PL_H] [PL_L] [Payload...] [Checksum] [0x7E]
  Checksum = (Type + Cmd + PL_H + PL_L + sum(Payload)) & 0xFF

Inventory 명령: BB 00 22 00 00 22 7E
태그 응답:      BB 02 22 00 [len] [RSSI] [PC_H] [PC_L] [EPC 12B] [CRC] 7E

실기기 프로토콜 검증 방법 (내일 연결 후):
  python -c "
  import serial, time
  s = serial.Serial('/dev/ttyUSB0', 57600, timeout=2)
  s.write(bytes([0xBB,0x00,0x22,0x00,0x00,0x22,0x7E]))
  time.sleep(1); print(s.read(100).hex())
  "
  응답이 안 오면 baud=115200 시도
"""

import serial
import time
import logging
import os

logger = logging.getLogger(__name__)

# Inventory 단일 라운드 명령
INVENTORY_CMD = bytes([0xBB, 0x00, 0x22, 0x00, 0x00, 0x22, 0x7E])

FRAME_START = 0xBB
FRAME_END   = 0x7E
RESP_TYPE   = 0x02
RESP_CMD    = 0x22


class FI805FReader:
    def __init__(self, port="/dev/ttyUSB0", baud=57600, timeout=1.0):
        self.port    = port
        self.baud    = baud
        self.timeout = timeout
        self._ser    = None

    def connect(self) -> bool:
        try:
            self._ser = serial.Serial(
                self.port, self.baud,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            logger.info("FI-805F 연결 완료: %s @ %d baud", self.port, self.baud)
            return True
        except serial.SerialException as e:
            logger.error("FI-805F 연결 실패: %s", e)
            return False

    def _send_inventory(self):
        if self._ser and self._ser.is_open:
            self._ser.write(INVENTORY_CMD)

    def _read_frame(self) -> bytes | None:
        """0xBB ~ 0x7E 한 프레임 읽기. 타임아웃 또는 파싱 실패 시 None."""
        if not self._ser:
            return None
        try:
            # 시작 바이트 탐색
            deadline = time.time() + self.timeout
            while time.time() < deadline:
                b = self._ser.read(1)
                if b and b[0] == FRAME_START:
                    break
            else:
                return None

            # 헤더 4바이트 읽기 (Type, Cmd, PL_H, PL_L)
            header = self._ser.read(4)
            if len(header) < 4:
                return None

            pl_len = (header[2] << 8) | header[3]
            if pl_len > 64:  # 비정상 프레임 방어
                return None

            # Payload + Checksum(1) + End(1)
            rest = self._ser.read(pl_len + 2)
            if len(rest) < pl_len + 2:
                return None

            frame = bytes([FRAME_START]) + header + rest
            if frame[-1] != FRAME_END:
                return None
            return frame
        except serial.SerialException as e:
            logger.warning("시리얼 읽기 오류: %s", e)
            return None

    def _parse_epc(self, frame: bytes) -> str | None:
        """
        프레임에서 EPC 추출.
        응답 구조: BB 02 22 [PL_H] [PL_L] [RSSI] [PC_H] [PC_L] [EPC...] [CRC_H] [CRC_L] [Checksum] 7E
        EPC 시작 인덱스: 8 (BB=0, Type=1, Cmd=2, PL_H=3, PL_L=4, RSSI=5, PC_H=6, PC_L=7)
        """
        if len(frame) < 10:
            return None
        if frame[1] != RESP_TYPE or frame[2] != RESP_CMD:
            return None

        pl_len = (frame[3] << 8) | frame[4]
        # Payload: RSSI(1) + PC(2) + EPC(pl_len - 5) + CRC(2)
        epc_len = pl_len - 5
        if epc_len <= 0:
            return None

        epc_start = 8  # BB Type Cmd PL_H PL_L RSSI PC_H PC_L
        epc_bytes = frame[epc_start: epc_start + epc_len]
        return epc_bytes.hex().upper()

    def collect_tags(self, window_sec: float = 3.0) -> list[str]:
        """
        window_sec 동안 inventory 명령을 0.5초마다 보내며 태그 수집.
        중복 제거 후 리스트 반환.
        """
        tags: set[str] = set()
        deadline = time.time() + window_sec
        poll_interval = 0.5

        while time.time() < deadline:
            self._send_inventory()
            frame = self._read_frame()
            if frame:
                epc = self._parse_epc(frame)
                if epc:
                    tags.add(epc)
            remaining = deadline - time.time()
            time.sleep(min(poll_interval, max(remaining, 0)))

        return list(tags)

    def close(self):
        if self._ser and self._ser.is_open:
            self._ser.close()
            logger.info("FI-805F 연결 종료")


class MockFI805FReader:
    """
    실기기 없을 때 사용하는 Mock 리더.
    /dev/ttyUSB0 없거나 MOCK_MODE=true 일 때 자동 전환.
    Supabase master_tags에 등록된 DUMMY 태그 3개 중 2개만 반환 (누락 시뮬레이션).
    """
    DUMMY_TAGS = [
        "DUMMY-TAG-UID-0001",
        "DUMMY-TAG-UID-0002",
        "DUMMY-TAG-UID-0003",
    ]

    def connect(self) -> bool:
        logger.warning("[MOCK] Mock RFID 리더 사용 중 — 실기기 연결 없음")
        return True

    def collect_tags(self, window_sec: float = 3.0) -> list[str]:
        logger.info("[MOCK] %s초 스캔 시뮬레이션 중...", window_sec)
        time.sleep(window_sec)
        # DUMMY-TAG-UID-0003 누락 시뮬레이션
        return self.DUMMY_TAGS[:2]

    def close(self):
        pass


def create_reader(port: str = "/dev/ttyUSB0", baud: int = 57600) -> FI805FReader | MockFI805FReader:
    """
    환경에 맞는 리더 인스턴스 반환.
    MOCK_MODE=true 이거나 포트가 없으면 MockFI805FReader 반환.
    """
    mock_mode = os.getenv("MOCK_MODE", "false").lower() == "true"
    port_exists = os.path.exists(port)

    if mock_mode or not port_exists:
        reason = "MOCK_MODE=true" if mock_mode else f"{port} 없음"
        logger.warning("Mock 모드 진입 (%s)", reason)
        return MockFI805FReader()

    reader = FI805FReader(port, baud)
    if not reader.connect():
        logger.warning("FI-805F 연결 실패 → Mock 모드로 전환")
        return MockFI805FReader()
    return reader
