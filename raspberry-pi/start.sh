#!/bin/bash
# SmartScan Hub 통합 실행 스크립트
# 사용법:
#   sudo bash start.sh          → 자동 감지 (USB 있으면 실모드, 없으면 Mock)
#   sudo bash start.sh mock     → 강제 Mock 모드
#   sudo bash start.sh real     → 강제 실모드 (USB 없으면 오류)
#   sudo bash start.sh verify   → FI-805F 프로토콜 응답 덤프만
#   sudo bash start.sh reset    → config 초기화 → AP 모드 재진입
#   sudo bash start.sh logs     → 실행 중인 컨테이너 로그 보기
#   sudo bash start.sh stop     → 컨테이너 중지

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-auto}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

log()  { echo -e "${GREEN}[OK]${NC}  $1"; }
warn() { echo -e "${YELLOW}[!!]${NC}  $1"; }
err()  { echo -e "${RED}[ERR]${NC} $1"; }
info() { echo -e "${CYAN}[--]${NC}  $1"; }

# ── 공통 체크 ──────────────────────────────────────────────────────────────
check_docker() {
  if ! command -v docker &>/dev/null; then
    warn "Docker가 없습니다. setup.sh 를 먼저 실행하세요."
    echo "  sudo bash setup.sh"
    exit 1
  fi
  if ! docker info &>/dev/null 2>&1; then
    err "Docker 데몬이 실행중이지 않습니다."
    echo "  sudo systemctl start docker"
    exit 1
  fi
}

check_env() {
  if [ ! -f "$SCRIPT_DIR/.env" ]; then
    warn ".env 파일이 없습니다. .env.example 에서 복사합니다..."
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    log ".env 생성 완료"
  fi
}

detect_usb() {
  [ -e /dev/ttyUSB0 ] && return 0 || return 1
}

# ── 모드별 처리 ────────────────────────────────────────────────────────────
case "$MODE" in

# ────────────────────────────── auto ──────────────────────────────────────
auto)
  check_docker
  check_env
  echo ""
  echo "===== SmartScan Hub 시작 ====="

  if detect_usb; then
    log "USB-RS232 감지됨 (/dev/ttyUSB0) → 실모드로 시작합니다"
    MOCK_FLAG="false"
  else
    warn "/dev/ttyUSB0 없음 → Mock 모드로 시작합니다"
    MOCK_FLAG="true"
  fi

  cd "$SCRIPT_DIR"
  MOCK_MODE=$MOCK_FLAG docker compose up --build -d
  log "컨테이너 시작 완료"
  echo ""
  info "로그 보기:  sudo bash start.sh logs"
  info "중지:       sudo bash start.sh stop"
  ;;

# ────────────────────────────── mock ──────────────────────────────────────
mock)
  check_docker
  check_env
  echo ""
  echo "===== SmartScan Hub [MOCK MODE] ====="
  warn "Mock 모드: 더미 태그 2개 전송 (실기기 없이 API/이메일 테스트)"
  cd "$SCRIPT_DIR"
  MOCK_MODE=true docker compose up --build
  ;;

# ────────────────────────────── real ──────────────────────────────────────
real)
  check_docker
  check_env
  echo ""
  echo "===== SmartScan Hub [REAL MODE] ====="
  if ! detect_usb; then
    err "/dev/ttyUSB0 이 없습니다. USB-RS232 컨버터를 먼저 꽂아주세요."
    exit 1
  fi
  log "USB-RS232 감지됨"
  cd "$SCRIPT_DIR"
  MOCK_MODE=false docker compose up --build
  ;;

# ────────────────────────────── verify ────────────────────────────────────
verify)
  echo ""
  echo "===== FI-805F 프로토콜 검증 ====="
  if ! detect_usb; then
    err "/dev/ttyUSB0 이 없습니다."
    exit 1
  fi
  check_docker
  log "FI-805F에 Inventory 커맨드 전송 중..."
  # 실행 중인 rfid-scanner 컨테이너가 포트를 점유하고 있으면 일시 중지
  docker stop smartscan-scanner 2>/dev/null || true

  docker run --rm --privileged \
    -v /dev:/dev \
    python:3.11-slim \
    sh -c "pip install -q pyserial && python3 -" <<'PYEOF'
import serial, time, sys

BAUD_RATES = [57600, 115200, 9600, 38400]
INVENTORY_CMD = bytes([0xBB, 0x00, 0x22, 0x00, 0x00, 0x22, 0x7E])

for baud in BAUD_RATES:
    print(f"\n[시도] baud={baud}...")
    try:
        s = serial.Serial('/dev/ttyUSB0', baud, timeout=2)
        s.write(INVENTORY_CMD)
        time.sleep(1.5)
        data = s.read(200)
        s.close()
        if data:
            print(f"  응답 hex : {data.hex()}")
            print(f"  응답 길이: {len(data)} bytes")
            if data[0] == 0xBB:
                print(f"  판정 : ✓ FI-805F 응답 정상 (baud={baud})")
                sys.exit(0)
            else:
                print(f"  판정 : △ 응답 있지만 시작 바이트가 0xBB가 아님")
        else:
            print(f"  판정 : ✗ 응답 없음")
    except Exception as e:
        print(f"  오류: {e}")

print("\n모든 baud rate에서 응답 없음.")
print("케이블 연결 및 컨버터 드라이버를 확인하세요.")
sys.exit(1)
PYEOF
  # verify 후 scanner 재시작
  cd "$SCRIPT_DIR" && docker start smartscan-scanner 2>/dev/null || true
  ;;


# ────────────────────────────── reset ─────────────────────────────────────
reset)
  echo ""
  echo "===== SmartScan Hub 초기화 ====="
  warn "Wi-Fi 설정을 초기화하고 AP 모드(SmartScan-Setup)로 돌아갑니다."
  read -p "계속하시겠습니까? [y/N] " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    info "취소됨"
    exit 0
  fi

  rm -f /etc/smartscan/config.env
  log "config.env 삭제 완료"

  cd "$SCRIPT_DIR"
  if docker compose ps | grep -q "Up"; then
    docker compose restart captive-portal
    log "captive-portal 재시작 완료 → SmartScan-Setup AP 생성 대기 중"
  else
    warn "컨테이너가 실행 중이 아닙니다. 'sudo bash start.sh auto' 로 시작하세요."
  fi
  ;;

# ────────────────────────────── logs ──────────────────────────────────────
logs)
  cd "$SCRIPT_DIR"
  echo "Ctrl+C 로 종료"
  docker compose logs -f
  ;;

# ────────────────────────────── stop ──────────────────────────────────────
stop)
  cd "$SCRIPT_DIR"
  docker compose down
  log "컨테이너 중지 완료"
  ;;

# ────────────────────────────── help ──────────────────────────────────────
*)
  echo ""
  echo "사용법: sudo bash start.sh [명령]"
  echo ""
  echo "  auto    USB 자동 감지 → 실모드 or Mock 모드 (기본값)"
  echo "  mock    강제 Mock 모드 (더미 태그 전송)"
  echo "  real    강제 실모드 (USB 없으면 오류)"
  echo "  verify  FI-805F 프로토콜 응답 확인 (baud rate 자동 탐지)"
  echo "  reset   Wi-Fi 설정 초기화 → AP 모드로 복귀"
  echo "  logs    실행 중인 컨테이너 로그 스트리밍"
  echo "  stop    컨테이너 중지"
  ;;
esac
