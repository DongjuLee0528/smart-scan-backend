"""
SmartScan Hub API Gateway 클라이언트

기존 Lambda scan_service.py 와 완벽 호환:
  POST {API_GW_URL}/inbound
  Body: {"device_serial": str, "tags": list[str]}
  Response: {"message": str}
"""

import time
import logging
import requests

logger = logging.getLogger(__name__)

_RETRY_DELAYS = [1, 2, 4]  # 지수 백오프 (초)


class SmartScanClient:
    def __init__(self, device_serial: str, api_gw_url: str):
        self.device_serial = device_serial
        self.inbound_url   = f"{api_gw_url.rstrip('/')}/inbound"

    def send_scan(self, tags: list[str]) -> dict | None:
        """
        태그 목록을 /inbound 로 전송.
        성공 시 응답 dict 반환, 최종 실패 시 None 반환.
        """
        payload = {
            "device_serial": self.device_serial,
            "tags": tags,
        }
        logger.info("POST %s | tags=%s", self.inbound_url, tags)

        for attempt, delay in enumerate(_RETRY_DELAYS, start=1):
            try:
                resp = requests.post(
                    self.inbound_url,
                    json=payload,
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    logger.info("응답 200: %s", data.get("message", ""))
                    return data
                elif resp.status_code < 500:
                    # 4xx — 재시도 불필요 (device_serial 오류 등)
                    logger.error("응답 %d (재시도 안 함): %s", resp.status_code, resp.text)
                    return None
                else:
                    logger.warning("응답 %d (재시도 %d/%d)...", resp.status_code, attempt, len(_RETRY_DELAYS))
            except requests.RequestException as e:
                logger.warning("요청 실패 (재시도 %d/%d): %s", attempt, len(_RETRY_DELAYS), e)

            if attempt < len(_RETRY_DELAYS):
                time.sleep(delay)

        logger.error("최대 재시도 초과. /inbound 전송 실패.")
        return None
