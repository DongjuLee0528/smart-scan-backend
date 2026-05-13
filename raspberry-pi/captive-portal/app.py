"""
캡티브 포털 Flask 웹 서버

라우트:
  GET  /         → 설정 완료이면 done.html, 미설정이면 setup.html
  POST /setup    → Wi-Fi 자격증명 + device_serial 저장 → 연결 후 완료 페이지
  GET  /status   → JSON {configured, wifi_ssid, device_serial}
  POST /reset    → config.env 삭제 → AP 모드 재시작
"""

import os
import re
import threading
import logging
from flask import Flask, request, render_template, jsonify, redirect, url_for

from portal_manager import (
    detect_wlan_interface,
    is_configured,
    start_ap_mode,
    save_and_connect,
    CONFIG_PATH,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

API_GW_URL   = os.getenv("API_GW_URL", "https://f7o6rm5r6a.execute-api.ap-northeast-2.amazonaws.com/prod")
PORTAL_PORT  = int(os.getenv("PORTAL_PORT", "80"))

# 시리얼 번호 허용 문자: 영숫자, 하이픈, 언더스코어 (validator.py 동일 규칙)
_SERIAL_RE = re.compile(r'^[a-zA-Z0-9_-]+$')

_iface = None  # 전역 Wi-Fi 인터페이스명


@app.route("/")
def index():
    if is_configured():
        cfg = _load_config()
        return render_template("done.html", device_serial=cfg.get("DEVICE_SERIAL", ""))
    return render_template("setup.html", ap_ip=os.getenv("AP_IP", "192.168.4.1"))


@app.route("/setup", methods=["POST"])
def setup():
    ssid          = request.form.get("ssid", "").strip()
    password      = request.form.get("password", "")
    device_serial = request.form.get("device_serial", "").strip()
    wifi_type     = request.form.get("wifi_type", "personal")
    username      = request.form.get("username", "").strip() if wifi_type == "enterprise" else ""

    # 유효성 검사
    errors = []
    if not ssid:
        errors.append("Wi-Fi 이름을 입력하세요.")
    if wifi_type == "enterprise" and not username:
        errors.append("WPA-Enterprise는 아이디가 필요합니다.")
    if not device_serial:
        errors.append("기기 시리얼 번호를 입력하세요.")
    elif not _SERIAL_RE.match(device_serial):
        errors.append("시리얼 번호는 영문, 숫자, 하이픈(-), 언더스코어(_)만 허용됩니다.")

    if errors:
        return render_template("setup.html",
                               ap_ip=os.getenv("AP_IP", "192.168.4.1"),
                               errors=errors,
                               ssid=ssid,
                               device_serial=device_serial), 400

    logger.info("설정 저장 시작: ssid=%s, type=%s, device_serial=%s", ssid, wifi_type, device_serial)

    # 백그라운드에서 Wi-Fi 연결 (응답 먼저 반환 후 처리)
    def _connect():
        save_and_connect(_iface, ssid, password, device_serial, API_GW_URL, username=username)

    threading.Thread(target=_connect, daemon=True).start()

    return render_template("done.html", device_serial=device_serial)


@app.route("/status")
def status():
    cfg = _load_config() if is_configured() else {}
    return jsonify({
        "configured":    is_configured(),
        "wifi_ssid":     cfg.get("WIFI_SSID", ""),
        "device_serial": cfg.get("DEVICE_SERIAL", ""),
    })


@app.route("/generate_204")
@app.route("/hotspot-detect.html")
@app.route("/library/test/success.html")
@app.route("/ncsi.txt")
@app.route("/connecttest.txt")
def captive_check():
    """iOS/Android 캡티브 포털 자동 감지 URL — 302로 설정 페이지 이동."""
    return redirect("/", code=302)


@app.route("/reset", methods=["POST"])
def reset():
    """공장 초기화: config.env 삭제 → AP 모드 재시작."""
    if os.path.exists(CONFIG_PATH):
        os.remove(CONFIG_PATH)
        logger.info("config.env 삭제 완료")

    def _restart_ap():
        import time; time.sleep(1)
        start_ap_mode(_iface)

    threading.Thread(target=_restart_ap, daemon=True).start()
    return redirect(url_for("index"))


def _load_config() -> dict:
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    cfg[k.strip()] = v.strip()
    return cfg


if __name__ == "__main__":
    _iface = detect_wlan_interface()

    if not is_configured():
        logger.info("미설정 상태 — AP 모드 시작")
        start_ap_mode(_iface)
    else:
        logger.info("이미 설정됨 — AP 모드 없이 상태 서버만 실행")

    app.run(host="0.0.0.0", port=PORTAL_PORT, debug=False)
