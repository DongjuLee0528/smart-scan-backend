"""
SmartScan Hub RFID 스캐너 메인 루프

실행 흐름:
  1. /etc/smartscan/config.env 로드 (파일 생성될 때까지 대기)
  2. MOCK_MODE 또는 /dev/ttyUSB0 여부로 리더 선택
  3. [루프] collect_tags(3초) → POST /inbound → 로그 출력 → 2초 대기
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
SCAN_INTERVAL_SEC = 2


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
    rfid_power    = cfg.get("RFID_POWER") or None   # hex "00"~"1B", 없으면 리더 기본값 유지

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

    logger.info("스캔 루프 시작 (window=%.1fs, interval=%ds)", scan_window, SCAN_INTERVAL_SEC)

    while True:
        try:
            tags = reader.collect_tags(window_sec=scan_window)

            if tags:
                logger.info("태그 감지: %s", tags)
                result = client.send_scan(tags)
                if result:
                    msg = result.get("message", "")
                    if "누락" in msg:
                        logger.warning(">>> %s", msg)
                    else:
                        logger.info(">>> %s", msg)
            else:
                logger.debug("태그 없음")

        except Exception as e:
            logger.error("스캔 루프 오류: %s", e)

        time.sleep(SCAN_INTERVAL_SEC)


if __name__ == "__main__":
    main()
