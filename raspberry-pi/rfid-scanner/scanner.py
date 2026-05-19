"""
SmartScan Hub RFID 스캐너 메인 루프

실행 흐름 (이벤트 기반 상태 머신):
  1. /etc/smartscan/config.env 로드 (파일 생성될 때까지 대기)
  2. MOCK_MODE 또는 /dev/ttyUSB0 여부로 리더 선택
  3. [IDLE] 태그 감지 대기
     → 태그 감지 시: POST /inbound 1회 전송 (SCANNING)
     → [WAITING_CLEAR] 태그 소멸까지 대기 (CLEAR_WAIT_SEC 동안 없으면 IDLE 복귀)
  외출·귀가 각 1회씩 이벤트 발생, 태그 방치 시 반복 전송 없음
"""

import os
import time
import logging
import signal
import sys

from fi805f_reader import create_reader
from api_client import SmartScanClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

CONFIG_PATH       = "/etc/smartscan/config.env"
CONFIG_RETRY_SEC  = 30
SCAN_INTERVAL_SEC = 2   # IDLE 상태 폴링 간격
CLEAR_POLL_SEC    = 2   # WAITING_CLEAR 상태 폴링 간격


def load_config() -> dict:
    """config.env 를 key=value 형식으로 파싱."""
    cfg = {}
    with open(CONFIG_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                cfg[k.strip()] = v.strip()
    return cfg


def wait_for_config() -> dict:
    """config.env 가 생성될 때까지 대기. 캡티브 포털 설정 완료 후 파일 생성됨."""
    while True:
        if os.path.exists(CONFIG_PATH):
            cfg = load_config()
            if cfg.get("WIFI_CONFIGURED") == "true" and cfg.get("DEVICE_SERIAL"):
                logger.info("설정 로드 완료: device_serial=%s", cfg["DEVICE_SERIAL"])
                return cfg
        logger.info("config.env 대기 중... (%s초 후 재시도)", CONFIG_RETRY_SEC)
        time.sleep(CONFIG_RETRY_SEC)


def main():
    logger.info("=== SmartScan Hub RFID Scanner 시작 ===")

    cfg = wait_for_config()

    device_serial = cfg["DEVICE_SERIAL"]
    api_gw_url    = cfg.get("API_GW_URL", os.getenv("API_GW_URL", ""))
    scan_window   = float(cfg.get("SCAN_WINDOW_SEC", "3"))
    rfid_port     = cfg.get("RFID_PORT", "/dev/ttyUSB0")
    rfid_baud     = int(cfg.get("RFID_BAUD", "38400"))
    rfid_power     = cfg.get("RFID_POWER") or None   # hex "00"~"1B", 없으면 리더 기본값 유지
    clear_wait_sec = int(cfg.get("CLEAR_WAIT_SEC", "60"))

    if not api_gw_url:
        logger.error("API_GW_URL 미설정. 종료.")
        sys.exit(1)

    reader = create_reader(port=rfid_port, baud=rfid_baud, power=rfid_power)
    client = SmartScanClient(device_serial, api_gw_url)

    def _shutdown(sig, frame):
        logger.info("종료 신호 수신. 리더 연결 닫는 중...")
        reader.close()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info(
        "이벤트 기반 스캔 시작 (window=%.1fs, clear_wait=%ds)",
        scan_window, clear_wait_sec,
    )

    while True:
        # ── IDLE: 태그 등장 대기 ──────────────────────────────────────
        try:
            tags = reader.collect_tags(window_sec=scan_window)
        except Exception as e:
            logger.error("스캔 오류: %s", e)
            time.sleep(SCAN_INTERVAL_SEC)
            continue

        if not tags:
            logger.debug("태그 없음 — 대기 중")
            time.sleep(SCAN_INTERVAL_SEC)
            continue

        # ── SCANNING: 태그 감지 → 1회 전송 ──────────────────────────
        logger.info("스캔 이벤트 시작: %s", tags)
        try:
            result = client.send_scan(tags)
            if result:
                msg = result.get("message", "")
                if "Missing" in msg or "누락" in msg:
                    logger.warning(">>> %s", msg)
                else:
                    logger.info(">>> %s", msg)
        except Exception as e:
            logger.error("전송 오류: %s", e)

        # ── WAITING_CLEAR: 태그 소멸 확인 ────────────────────────────
        logger.info("WAITING_CLEAR — 태그 소멸 대기 중 (최대 무제한, 감지 없으면 IDLE 복귀)")
        clear_deadline = time.time() + clear_wait_sec
        while True:
            time.sleep(CLEAR_POLL_SEC)
            try:
                remaining = reader.collect_tags(window_sec=1.0)
            except Exception:
                remaining = []

            if not remaining:
                if time.time() >= clear_deadline:
                    logger.info("태그 소멸 확인 — IDLE 복귀 (다음 이벤트 대기)")
                    break
            else:
                # 아직 태그 있음 → 타이머 리셋
                clear_deadline = time.time() + clear_wait_sec
                logger.debug("태그 아직 감지 중 — 대기 연장")


if __name__ == "__main__":
    main()
