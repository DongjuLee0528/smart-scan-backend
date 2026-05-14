"""
FI-805F UHF RFID 리더기 드라이버 (ASCII 프로토콜)

통신 설정: 38400 baud, 8N1
커맨드:
  <LF>U<CR>  → 멀티태그 EPC 읽기 (권장)
  <LF>Q<CR>  → 단일태그 EPC 읽기
응답 형식 (U 커맨드):
  \nU<PC(4hex)><EPC><CRC16(4hex)>\r\n  (태그 1개당 1줄)
  \nU\r\n                               (응답 종료 마커)
EPC 추출: data[4:-4]  (PC 앞 4자, CRC16 뒤 4자 제거)
"""

import serial
import time
import logging
import os

logger = logging.getLogger(__name__)

CMD_MULTI  = b"U\r\n"   # Multi-tag inventory
CMD_SINGLE = b"Q\r\n"   # Single-tag EPC query


class FI805FReader:
    def __init__(self, port="/dev/ttyUSB0", baud=38400, timeout=1.0):
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

    def _parse_epc_line(self, line: bytes) -> str | None:
        """
        응답 라인에서 EPC 추출.
        형식: U<PC(4hex)><EPC><CRC16(4hex)>  (strip 후)
        """
        try:
            decoded = line.decode("ascii", errors="replace").strip()
            if not decoded or decoded[0] not in ("U", "Q"):
                return None
            data = decoded[1:]          # 커맨드 문자 제거
            # PC(4) + EPC(최소 8) + CRC16(4) → 최소 16자
            if len(data) < 16:
                return None
            epc = data[4:-4]            # PC 앞 4자, CRC16 뒤 4자 제거
            if len(epc) < 8:
                return None
            return epc.upper()
        except Exception:
            return None

    def collect_tags(self, window_sec: float = 3.0) -> list[str]:
        """
        window_sec 동안 멀티태그 인벤토리 반복 수행.
        각 U 커맨드 이후 응답 종료 마커 또는 2초 타임아웃까지 수집.
        """
        tags: set[str] = set()
        deadline = time.time() + window_sec

        while time.time() < deadline:
            if not self._ser or not self._ser.is_open:
                break

            self._ser.reset_input_buffer()
            self._ser.write(CMD_MULTI)

            # 응답 버퍼 수집 (최대 2초 또는 종료 마커 도달 시 종료)
            buf = b""
            scan_dl = time.time() + 2.0
            while time.time() < scan_dl:
                chunk = self._ser.read(256)
                if chunk:
                    buf += chunk
                    if b"\nU\r\n" in buf:   # 종료 마커 확인
                        break

            # 줄 단위 파싱
            for segment in buf.split(b"\n"):
                epc = self._parse_epc_line(segment)
                if epc:
                    tags.add(epc)

            time.sleep(0.5)

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


def create_reader(port: str = "/dev/ttyUSB0", baud: int = 38400) -> FI805FReader | MockFI805FReader:
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
