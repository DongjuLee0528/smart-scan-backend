"""
캡티브 포털 AP 모드 전환 관리자

동작 순서 (AP 모드 진입):
  1. wlan 인터페이스 자동 탐지
  2. wpa_supplicant / NetworkManager 중지
  3. 정적 IP 설정 (192.168.4.1/24)
  4. hostapd 시작 (AP: SmartScan-Setup)
  5. dnsmasq 시작 (DHCP: 192.168.4.2~20)

Wi-Fi 저장 후 복귀:
  1. hostapd / dnsmasq 중지
  2. wpa_supplicant.conf 작성
  3. wpa_supplicant 재시작 → DHCP
"""

import os
import subprocess
import time
import logging

logger = logging.getLogger(__name__)

CONFIG_PATH = "/etc/smartscan/config.env"
WPA_CONF    = "/etc/wpa_supplicant/wpa_supplicant.conf"

AP_SSID = os.getenv("AP_SSID", "SmartScan-Setup")
AP_IP   = os.getenv("AP_IP",   "192.168.4.1")

HOSTAPD_CONF = "/tmp/smartscan_hostapd.conf"
DNSMASQ_CONF = "/tmp/smartscan_dnsmasq.conf"


def _run(cmd: str, check=False) -> int:
    logger.debug("$ %s", cmd)
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        logger.debug(result.stdout.strip())
    if result.stderr:
        logger.debug(result.stderr.strip())
    return result.returncode


def detect_wlan_interface() -> str:
    """ip link 으로 wlan* 인터페이스 자동 탐지. 없으면 'wlan0' 반환."""
    result = subprocess.run("ip link show", shell=True, capture_output=True, text=True)
    for line in result.stdout.splitlines():
        parts = line.split(":")
        if len(parts) >= 2:
            name = parts[1].strip().split("@")[0]
            if name.startswith("wlan") or name.startswith("wl"):
                logger.info("Wi-Fi 인터페이스 감지: %s", name)
                return name
    logger.warning("Wi-Fi 인터페이스 미감지, wlan0 사용")
    return "wlan0"


def is_configured() -> bool:
    """config.env 존재 + WIFI_CONFIGURED=true 확인."""
    if not os.path.exists(CONFIG_PATH):
        return False
    with open(CONFIG_PATH) as f:
        for line in f:
            if line.strip() == "WIFI_CONFIGURED=true":
                return True
    return False


def start_ap_mode(iface: str):
    """AP 모드 시작. hostapd + dnsmasq 실행."""
    logger.info("[AP] %s 에서 AP 모드 시작 (%s)", iface, AP_SSID)

    # Wi-Fi 소프트 블록 해제
    _run("rfkill unblock wifi || true")

    # NetworkManager / wpa_supplicant systemd 서비스 정지 (pkill 은 즉시 재시작됨)
    _run("systemctl stop NetworkManager || true")
    _run("systemctl stop wpa_supplicant || true")
    _run(f"systemctl stop wpa_supplicant@{iface} || true")
    _run(f"nmcli device set {iface} managed no 2>/dev/null || true")
    time.sleep(2)

    # 인터페이스 정적 IP 설정
    _run(f"ip link set {iface} down")
    _run(f"ip addr flush dev {iface}")
    _run(f"ip link set {iface} up")
    _run(f"ip addr add {AP_IP}/24 dev {iface}")

    # hostapd 설정 파일 (country_code=KR 필수 — 없으면 nl80211 채널 오류)
    with open(HOSTAPD_CONF, "w") as f:
        f.write(f"""interface={iface}
driver=nl80211
ssid={AP_SSID}
hw_mode=g
channel=6
country_code=KR
ieee80211d=1
ieee80211n=1
auth_algs=1
wmm_enabled=0
""")

    # dnsmasq 설정 파일
    # bind-interfaces: 53/udp 를 AP IP 에만 바인딩 (systemd-resolved 충돌 방지)
    # dhcp-option=3,6: 게이트웨이·DNS 를 AP IP 로 알려줘야 폰이 자동 팝업
    dhcp_start = AP_IP.rsplit(".", 1)[0] + ".2"
    dhcp_end   = AP_IP.rsplit(".", 1)[0] + ".20"
    with open(DNSMASQ_CONF, "w") as f:
        f.write(f"""interface={iface}
listen-address={AP_IP}
bind-interfaces
no-resolv
no-poll
dhcp-range={dhcp_start},{dhcp_end},255.255.255.0,24h
dhcp-option=3,{AP_IP}
dhcp-option=6,{AP_IP}
address=/#/{AP_IP}
""")

    # 서비스 시작
    rc_h = _run(f"hostapd -B {HOSTAPD_CONF}")
    rc_d = _run(f"dnsmasq --conf-file={DNSMASQ_CONF} --pid-file=/tmp/dnsmasq.pid")

    if rc_h != 0 or rc_d != 0:
        logger.error("[AP] hostapd(%d) 또는 dnsmasq(%d) 시작 실패", rc_h, rc_d)
    else:
        logger.info("[AP] AP 준비 완료 — 폰에서 '%s' 접속 후 %s 로 이동하세요", AP_SSID, AP_IP)


def stop_ap_mode():
    """hostapd / dnsmasq 종료."""
    logger.info("[AP] AP 모드 종료 중...")
    _run("pkill -f hostapd || true")
    _run("pkill -f dnsmasq || true")
    time.sleep(1)


def save_and_connect(iface: str, ssid: str, password: str, device_serial: str, api_gw_url: str, username: str = ""):
    """
    Wi-Fi 자격증명과 device_serial 저장 후 클라이언트 모드로 전환.
    username 이 있으면 WPA-Enterprise(PEAP/MSCHAPv2), 없으면 WPA-PSK.
    """
    logger.info("[WIFI] SSID=%s 로 연결 시도 (type=%s)...", ssid, "enterprise" if username else "personal")

    stop_ap_mode()

    # wpa_supplicant.conf 작성
    os.makedirs(os.path.dirname(WPA_CONF), exist_ok=True)
    with open(WPA_CONF, "w") as f:
        if username:
            f.write(f"""ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=KR

network={{
    ssid="{ssid}"
    key_mgmt=WPA-EAP
    eap=PEAP
    identity="{username}"
    password="{password}"
    phase2="auth=MSCHAPV2"
    ca_cert="/etc/ssl/certs/ca-certificates.crt"
}}
""")
        else:
            f.write(f"""ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=KR

network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}
""")

    # config.env 저장
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        f.write(f"""DEVICE_SERIAL={device_serial}
API_GW_URL={api_gw_url}
WIFI_SSID={ssid}
WIFI_CONFIGURED=true
SCAN_WINDOW_SEC=3
MOCK_MODE=false
""")
    logger.info("[CONFIG] %s 저장 완료", CONFIG_PATH)

    # Wi-Fi 연결 (기존 wpa_supplicant 소켓 제거 후 재시작)
    _run(f"rm -f /var/run/wpa_supplicant/{iface}")
    _run(f"ip link set {iface} up")
    _run(f"wpa_supplicant -B -i {iface} -c {WPA_CONF}")

    # WPA 인증 완료 대기 (최대 20초)
    connected = False
    for _ in range(20):
        time.sleep(1)
        result = subprocess.run(
            f"wpa_cli -i {iface} status",
            shell=True, capture_output=True, text=True
        )
        if "wpa_state=COMPLETED" in result.stdout:
            connected = True
            break

    if connected:
        rc = _run(f"dhclient {iface}")
        if rc != 0:
            _run(f"udhcpc -i {iface} &")
        logger.info("[WIFI] Wi-Fi 연결 완료: %s", ssid)
    else:
        logger.error("[WIFI] WPA 인증 실패 (비밀번호 오류?) — AP 모드로 복귀")
        with open(CONFIG_PATH, "w") as f:
            f.write("")  # 빈 파일 → is_configured() = False
        start_ap_mode(iface)
