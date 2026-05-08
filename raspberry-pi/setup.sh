#!/bin/bash
# SmartScan Hub 라즈베리파이 최초 설치 스크립트
# 실행: sudo bash setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== SmartScan Hub 설치 시작 ==="

# 1. Docker 설치 확인
if ! command -v docker &>/dev/null; then
  echo "[1/5] Docker 설치 중..."
  curl -fsSL https://get.docker.com | sh
  usermod -aG docker $SUDO_USER || true
  echo "Docker 설치 완료"
else
  echo "[1/5] Docker 이미 설치됨 ($(docker --version))"
fi

# 2. Tailscale 설치
if ! command -v tailscale &>/dev/null; then
  echo "[2/5] Tailscale 설치 중..."
  curl -fsSL https://tailscale.com/install.sh | sh
  systemctl enable --now tailscaled
  echo "Tailscale 설치 완료"
  echo "  → 인증 필요: sudo tailscale up"
  echo "  → 표시된 URL을 브라우저에서 열어 승인하세요"
else
  echo "[2/5] Tailscale 이미 설치됨 ($(tailscale version | head -1))"
  systemctl enable --now tailscaled 2>/dev/null || true
fi

# 3. /etc/smartscan 디렉토리 생성
echo "[3/5] 설정 디렉토리 생성..."
mkdir -p /etc/smartscan
chmod 755 /etc/smartscan

# 4. .env 파일 생성 (없으면)
if [ ! -f "$SCRIPT_DIR/.env" ]; then
  cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
  echo "[4/5] .env 파일 생성 완료"
else
  echo "[4/5] .env 파일 이미 존재"
fi

# 5. systemd 서비스 등록
echo "[5/5] systemd 서비스 등록..."
cat > /etc/systemd/system/smartscan.service << EOF
[Unit]
Description=SmartScan Hub Edge Service
After=network.target docker.service
Requires=docker.service

[Service]
WorkingDirectory=${SCRIPT_DIR}
ExecStartPre=/usr/bin/docker compose pull --quiet || true
ExecStart=/usr/bin/docker compose up --build
ExecStop=/usr/bin/docker compose down
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable smartscan.service

echo ""
echo "=== 설치 완료 ==="
echo ""
echo "[Tailscale 인증]"
echo "  sudo tailscale up"
echo "  → URL 열어 승인 후 고정 IP 확인: tailscale ip -4"
echo ""
echo "[SmartScan 시작]"
echo "  sudo systemctl start smartscan"
echo "  sudo journalctl -u smartscan -f"
echo ""
echo "또는 지금 바로 실행:"
echo "  cd $SCRIPT_DIR && docker compose up"
