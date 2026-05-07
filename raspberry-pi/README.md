# SmartScan Hub — 라즈베리파이 엣지 디바이스

FI-805F UHF RFID 리더기 + 라즈베리파이 4B로 동작하는 현관 소지품 체크 시스템.

## 하드웨어 연결

```
FI-805F RS232 → USB-to-RS232 컨버터 → 라즈베리파이 USB → /dev/ttyUSB0
```

## 최초 설치 (라즈베리파이에서 실행)

```bash
# 1. 레포 클론 또는 파일 복사
git clone https://github.com/DongjuLee0528/smart-scan-backend.git
cd smart-scan-backend/raspberry-pi

# 2. 설치 스크립트 실행
sudo bash setup.sh

# 3. 실행
sudo systemctl start smartscan
# 또는
docker compose up
```

## 초기 설정 (캡티브 포털)

1. 라즈베리파이 부팅 후 **SmartScan-Setup** Wi-Fi AP가 생성됩니다
2. 스마트폰으로 **SmartScan-Setup** 에 연결 (비밀번호 없음)
3. 브라우저에서 **192.168.4.1** 접속
4. Wi-Fi 이름, 비밀번호, 기기 시리얼 번호 입력 → 연결하기
5. 기기가 홈 네트워크에 연결되면 자동으로 RFID 스캔 시작

> **기기 시리얼 번호**: SmartScan 웹사이트(smartscan-hub.com) → 기기 관리 → 등록 시 사용한 번호

## Mock 모드 (실기기 없이 테스트)

```bash
MOCK_MODE=true docker compose up
```

- `/dev/ttyUSB0` 없어도 동작
- 더미 태그 3개 중 2개만 전송 (1개 누락 시뮬레이션)
- API Gateway 200 응답 및 이메일 알림 테스트 가능

## FI-805F 프로토콜 검증

실기기 연결 후 raw 덤프로 응답 확인:

```bash
docker run --rm --device=/dev/ttyUSB0 python:3.11-slim python3 -c "
import serial, time
s = serial.Serial('/dev/ttyUSB0', 57600, timeout=2)
s.write(bytes([0xBB, 0x00, 0x22, 0x00, 0x00, 0x22, 0x7E]))
time.sleep(1)
data = s.read(100)
print('응답 hex:', data.hex())
print('응답 길이:', len(data))
"
```

- 응답이 없으면 `baud=115200` 으로 변경 (`rfid-scanner/fi805f_reader.py` 의 `__init__` 기본값)
- 응답 첫 바이트가 `bb` 이면 프레임 파싱 정상

## 디렉토리 구조

```
raspberry-pi/
├── docker-compose.yml
├── .env.example
├── setup.sh
├── captive-portal/          # Wi-Fi 초기 설정 포털
│   ├── app.py               # Flask 서버 (포트 80)
│   ├── portal_manager.py    # AP 모드 전환
│   └── templates/
│       ├── setup.html       # Wi-Fi 설정 페이지
│       └── done.html        # 설정 완료 페이지
└── rfid-scanner/            # RFID 스캔 → API 전송
    ├── scanner.py           # 메인 루프
    ├── fi805f_reader.py     # FI-805F 드라이버 + Mock
    └── api_client.py        # API Gateway 클라이언트
```

## 로그 확인

```bash
# 전체 로그
docker compose logs -f

# 스캐너만
docker compose logs -f rfid-scanner

# 캡티브 포털만
docker compose logs -f captive-portal
```

## 설정 초기화

```bash
# config.env 삭제 → 다음 재시작 시 AP 모드로 진입
sudo rm /etc/smartscan/config.env
docker compose restart captive-portal
```
