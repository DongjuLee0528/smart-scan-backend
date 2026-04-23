# SmartScan Hub - Supabase 설정 가이드

## 사전 준비
- Supabase 계정 (supabase.com)
- Resend 계정 (resend.com) - 이메일 발송용

---

## Step 1. 프로젝트 접속

1. [supabase.com](https://supabase.com) 로그인
2. 좌측 상단에서 `smartscan-hub` 프로젝트 선택

---


## Step 2. DB 스키마 생성

1. 좌측 메뉴 → **SQL Editor** → **New Query**
2. 아래 SQL 전체 복사 후 붙여넣기
3. 우측 상단 **Run** 버튼 클릭

```sql
-- ============================================================
-- SmartScan Hub - Supabase PostgreSQL DDL
-- Supabase Auth(auth.users) 연동 구조
-- 생성 순서: profiles → families → family_members
--           → devices → items → tags
--           → scan_logs → notifications
-- ============================================================

-- 1. profiles (Supabase Auth 연동)
CREATE TABLE profiles (
    id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    name        VARCHAR(50) NOT NULL,
    email       VARCHAR(100) UNIQUE NOT NULL,
    phone       VARCHAR(20),
    age         INTEGER,
    role        VARCHAR(10) NOT NULL DEFAULT 'owner'
                    CHECK (role IN ('owner', 'member')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. families
CREATE TABLE families (
    id          BIGSERIAL PRIMARY KEY,
    owner_id    UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name        VARCHAR(50) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. family_members
CREATE TABLE family_members (
    id          BIGSERIAL PRIMARY KEY,
    family_id   BIGINT NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    profile_id  UUID REFERENCES profiles(id) ON DELETE SET NULL,
    name        VARCHAR(50) NOT NULL,
    phone       VARCHAR(20),
    email       VARCHAR(100),
    role        VARCHAR(10) NOT NULL DEFAULT 'member'
                    CHECK (role IN ('owner', 'member')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. devices
CREATE TABLE devices (
    id              BIGSERIAL PRIMARY KEY,
    serial_number   VARCHAR(20) UNIQUE NOT NULL,
    family_id       BIGINT NOT NULL REFERENCES families(id) ON DELETE CASCADE,
    name            VARCHAR(50),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. items
CREATE TABLE items (
    id          BIGSERIAL PRIMARY KEY,
    member_id   BIGINT NOT NULL REFERENCES family_members(id) ON DELETE CASCADE,
    name        VARCHAR(100) NOT NULL,
    is_required BOOLEAN NOT NULL DEFAULT TRUE,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. tags
CREATE TABLE tags (
    id          BIGSERIAL PRIMARY KEY,
    tag_uid     VARCHAR(50) UNIQUE NOT NULL,
    item_id     BIGINT NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    device_id   BIGINT NOT NULL REFERENCES devices(id) ON DELETE RESTRICT,
    label       VARCHAR(100),
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. scan_logs
CREATE TABLE scan_logs (
    id          BIGSERIAL PRIMARY KEY,
    device_id   BIGINT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    tag_uid     VARCHAR(50) NOT NULL,
    rssi        INTEGER,
    scanned_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8. notifications
CREATE TABLE notifications (
    id          BIGSERIAL PRIMARY KEY,
    member_id   BIGINT NOT NULL REFERENCES family_members(id) ON DELETE CASCADE,
    type        VARCHAR(20) NOT NULL
                    CHECK (type IN ('missing', 'remote', 'system')),
    title       VARCHAR(200) NOT NULL,
    message     TEXT,
    is_read     BOOLEAN NOT NULL DEFAULT FALSE,
    sent_via    VARCHAR(20),
    sent_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 인덱스
-- ============================================================
CREATE INDEX idx_families_owner_id          ON families(owner_id);
CREATE INDEX idx_family_members_family_id   ON family_members(family_id);
CREATE INDEX idx_family_members_profile_id  ON family_members(profile_id);
CREATE INDEX idx_devices_family_id          ON devices(family_id);
CREATE INDEX idx_devices_serial_number      ON devices(serial_number);
CREATE INDEX idx_items_member_id            ON items(member_id);
CREATE INDEX idx_items_is_active            ON items(is_active);
CREATE INDEX idx_tags_item_id               ON tags(item_id);
CREATE INDEX idx_tags_device_id             ON tags(device_id);
CREATE INDEX idx_tags_tag_uid               ON tags(tag_uid);
CREATE INDEX idx_scan_logs_device_id        ON scan_logs(device_id);
CREATE INDEX idx_scan_logs_tag_uid          ON scan_logs(tag_uid);
CREATE INDEX idx_scan_logs_scanned_at       ON scan_logs(scanned_at DESC);
CREATE INDEX idx_notifications_member_id    ON notifications(member_id);
CREATE INDEX idx_notifications_is_read      ON notifications(is_read);
```

---

## Step 3. 회원가입 시 프로필 자동 생성 트리거

SQL Editor → New Query → 아래 SQL 실행

```sql
-- 회원가입 시 profiles 테이블에 자동 INSERT
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, name, email)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'name', ''),
        NEW.email
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();
```

---

## Step 4. RLS (보안 정책) 설정

SQL Editor → New Query → 아래 SQL 실행

```sql
-- 모든 테이블 RLS 활성화
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE families ENABLE ROW LEVEL SECURITY;
ALTER TABLE family_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE items ENABLE ROW LEVEL SECURITY;
ALTER TABLE tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE scan_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- profiles: 본인 데이터만 조회/수정
-- ============================================================
CREATE POLICY "본인 프로필 조회" ON profiles
    FOR SELECT USING (id = auth.uid());

CREATE POLICY "본인 프로필 수정" ON profiles
    FOR UPDATE USING (id = auth.uid());

-- ============================================================
-- families: 본인이 owner인 가족만
-- ============================================================
CREATE POLICY "가족 조회" ON families
    FOR SELECT USING (owner_id = auth.uid());

CREATE POLICY "가족 생성" ON families
    FOR INSERT WITH CHECK (owner_id = auth.uid());

CREATE POLICY "가족 수정" ON families
    FOR UPDATE USING (owner_id = auth.uid());

CREATE POLICY "가족 삭제" ON families
    FOR DELETE USING (owner_id = auth.uid());

-- ============================================================
-- family_members: 본인 가족의 구성원만
-- ============================================================
CREATE POLICY "구성원 조회" ON family_members
    FOR SELECT USING (
        family_id IN (SELECT id FROM families WHERE owner_id = auth.uid())
    );

CREATE POLICY "구성원 추가" ON family_members
    FOR INSERT WITH CHECK (
        family_id IN (SELECT id FROM families WHERE owner_id = auth.uid())
    );

CREATE POLICY "구성원 수정" ON family_members
    FOR UPDATE USING (
        family_id IN (SELECT id FROM families WHERE owner_id = auth.uid())
    );

CREATE POLICY "구성원 삭제" ON family_members
    FOR DELETE USING (
        family_id IN (SELECT id FROM families WHERE owner_id = auth.uid())
    );

-- ============================================================
-- devices: 본인 가족의 기기만
-- ============================================================
CREATE POLICY "기기 조회" ON devices
    FOR SELECT USING (
        family_id IN (SELECT id FROM families WHERE owner_id = auth.uid())
    );

CREATE POLICY "기기 등록" ON devices
    FOR INSERT WITH CHECK (
        family_id IN (SELECT id FROM families WHERE owner_id = auth.uid())
    );

CREATE POLICY "기기 수정" ON devices
    FOR UPDATE USING (
        family_id IN (SELECT id FROM families WHERE owner_id = auth.uid())
    );

-- ============================================================
-- items: 본인 가족 구성원의 소지품만
-- ============================================================
CREATE POLICY "소지품 조회" ON items
    FOR SELECT USING (
        member_id IN (
            SELECT fm.id FROM family_members fm
            JOIN families f ON fm.family_id = f.id
            WHERE f.owner_id = auth.uid()
        )
    );

CREATE POLICY "소지품 등록" ON items
    FOR INSERT WITH CHECK (
        member_id IN (
            SELECT fm.id FROM family_members fm
            JOIN families f ON fm.family_id = f.id
            WHERE f.owner_id = auth.uid()
        )
    );

CREATE POLICY "소지품 수정" ON items
    FOR UPDATE USING (
        member_id IN (
            SELECT fm.id FROM family_members fm
            JOIN families f ON fm.family_id = f.id
            WHERE f.owner_id = auth.uid()
        )
    );

CREATE POLICY "소지품 삭제" ON items
    FOR DELETE USING (
        member_id IN (
            SELECT fm.id FROM family_members fm
            JOIN families f ON fm.family_id = f.id
            WHERE f.owner_id = auth.uid()
        )
    );

-- ============================================================
-- tags: 본인 가족 기기/소지품의 태그만
-- ============================================================
CREATE POLICY "태그 조회" ON tags
    FOR SELECT USING (
        device_id IN (
            SELECT d.id FROM devices d
            JOIN families f ON d.family_id = f.id
            WHERE f.owner_id = auth.uid()
        )
    );

CREATE POLICY "태그 등록" ON tags
    FOR INSERT WITH CHECK (
        device_id IN (
            SELECT d.id FROM devices d
            JOIN families f ON d.family_id = f.id
            WHERE f.owner_id = auth.uid()
        )
    );

CREATE POLICY "태그 수정" ON tags
    FOR UPDATE USING (
        device_id IN (
            SELECT d.id FROM devices d
            JOIN families f ON d.family_id = f.id
            WHERE f.owner_id = auth.uid()
        )
    );

-- ============================================================
-- scan_logs: 본인 가족 기기의 스캔 이력만
-- ============================================================
CREATE POLICY "스캔 이력 조회" ON scan_logs
    FOR SELECT USING (
        device_id IN (
            SELECT d.id FROM devices d
            JOIN families f ON d.family_id = f.id
            WHERE f.owner_id = auth.uid()
        )
    );

-- scan_logs INSERT는 Lambda smartscan-inbound (service_role)에서만 수행

-- ============================================================
-- notifications: 본인 가족 구성원의 알림만
-- ============================================================
CREATE POLICY "알림 조회" ON notifications
    FOR SELECT USING (
        member_id IN (
            SELECT fm.id FROM family_members fm
            JOIN families f ON fm.family_id = f.id
            WHERE f.owner_id = auth.uid()
        )
    );

CREATE POLICY "알림 읽음 처리" ON notifications
    FOR UPDATE USING (
        member_id IN (
            SELECT fm.id FROM family_members fm
            JOIN families f ON fm.family_id = f.id
            WHERE f.owner_id = auth.uid()
        )
    );
```

---

## Step 5. Auth 설정

### 이메일 인증
```
Authentication → Providers → Email
- Enable Email provider: ON
- Confirm email: ON
- Secure email change: ON
```

### SMTP 연동 (Resend)
```
Authentication → SMTP Settings
- Enable Custom SMTP: ON
- Host: smtp.resend.com
- Port: 465
- User: resend
- Password: [Resend API Key 입력]
- Sender email: noreply@smartscan-hub.com
- Sender name: SmartScan Hub
```

> Resend API Key 발급: resend.com → API Keys → Create API Key

---

## Step 6. Realtime 설정 (대시보드 실시간 갱신)

```
Database → Replication
```

아래 테이블 Realtime 활성화:
- `scan_logs` — 스캔 발생 시 대시보드 자동 갱신
- `notifications` — 새 알림 발생 시 실시간 표시

```sql
-- SQL로 활성화하는 경우
ALTER PUBLICATION supabase_realtime ADD TABLE scan_logs;
ALTER PUBLICATION supabase_realtime ADD TABLE notifications;
```

---

## Step 7. AWS Lambda 설정 (전체 유지)

> 기존 Lambda 4개를 모두 유지하고, DB 접속만 RDS → Supabase로 변경.
> Edge Functions 대신 Lambda를 유지하는 이유: 기존 Python 코드 재사용, CI/CD 그대로, 학습 비용 없음.

### 7-1. 공통 변경사항 (모든 Lambda)

각 Lambda의 `common/db.py`를 수정:
```python
# 기존: pymysql로 RDS 접속
import pymysql
conn = pymysql.connect(host=..., db='smart_scan')

# 변경: supabase-py로 Supabase 접속
import os
from supabase import create_client

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"]
)
```

각 Lambda의 `requirements.txt`에 추가:
```
supabase
```

### 7-2. Lambda별 역할

| Lambda | 함수명 | 역할 |
|--------|--------|------|
| **smartscan-inbound** | scan-process | RFID 스캔 수신 → scan_logs INSERT → 누락 체크 (RPC 함수 호출) |
| **smartscan-outbound** | missing-alert | 누락 감지 → notifications INSERT → Resend 이메일 발송 |
| **smartscan-remote** | send-remote (신규) | 부모→자녀 원격 알림 → notifications INSERT → Resend 이메일 |
| **smartscan-chatbot** | chatbot-skill-server | 카카오 챗봇 Webhook → DB 조회/등록 |

### 7-3. Lambda 환경변수 (AWS 콘솔에서 설정)

모든 Lambda 공통:

| 키 | 값 |
|----|-----|
| `SUPABASE_URL` | Supabase Project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service_role key |

추가 (outbound, remote):

| 키 | 값 |
|----|-----|
| `RESEND_API_KEY` | Resend API Key |

### 7-4. CI/CD (기존 워크플로우 유지)

```
.github/workflows/
├── deploy-inbound.yml    ← 그대로 유지
├── deploy-outbound.yml   ← 그대로 유지
├── deploy-chatbot.yml    ← 그대로 유지
└── deploy-remote.yml     ← 신규 (send-remote용)
```

> main 브랜치에 lambdas/ 하위 파일 변경 시 자동 배포

---

## Step 8. 환경변수 수집

```
Project Settings → API
```

아래 값을 팀 채널에 공유:

| 변수명 | 위치 | 용도 |
|--------|------|------|
| `SUPABASE_URL` | Project URL | 모든 클라이언트 |
| `SUPABASE_ANON_KEY` | anon public | 웹사이트 (supabase-js) |
| `SUPABASE_SERVICE_KEY` | service_role | Lambda 4개 (서버용) |

---

## Step 9. API Gateway 설정 (send-remote 추가)

> 기존 API Gateway에 원격 알림용 엔드포인트 추가

```
API Gateway → SmartScan-API → 리소스 추가:
POST /remote-alert → Lambda: smartscan-remote
```

또는 Terraform으로 추가:
```hcl
resource "aws_lambda_function" "smartscan_remote" {
  function_name = "smartscan-remote"
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.12"
  # ... (inbound와 동일 구조)
}
```

---

## Step 10. DB 성능 최적화

SQL Editor → New Query → 아래 SQL을 순서대로 실행

### 10-1. 복합 인덱스 (자주 쓰는 조회 가속)

```sql
-- 스캔 시 태그 → 소지품 → 구성원 매핑 (매 스캔마다 호출)
CREATE INDEX idx_tags_uid_item_device ON tags(tag_uid, item_id, device_id);

-- 가족 대시보드: 활성 소지품만 조회
CREATE INDEX idx_items_member_active ON items(member_id, is_active) WHERE is_active = TRUE;

-- 최근 스캔 이력 조회 (대시보드, 모니터링)
CREATE INDEX idx_scan_logs_device_time ON scan_logs(device_id, scanned_at DESC);

-- 안 읽은 알림 조회
CREATE INDEX idx_notifications_member_unread ON notifications(member_id, is_read) WHERE is_read = FALSE;
```

### 10-2. DB View (가족 대시보드 전용)

```sql
-- 가족 전체 상태를 한 번에 조회하는 View
CREATE OR REPLACE VIEW family_dashboard AS
SELECT
    fm.id AS member_id,
    fm.name AS member_name,
    fm.family_id,
    fm.email AS member_email,
    i.id AS item_id,
    i.name AS item_name,
    i.is_required,
    t.tag_uid,
    (
        SELECT MAX(sl.scanned_at)
        FROM scan_logs sl
        WHERE sl.tag_uid = t.tag_uid
    ) AS last_seen
FROM family_members fm
LEFT JOIN items i ON i.member_id = fm.id AND i.is_active = TRUE
LEFT JOIN tags t ON t.item_id = i.id AND t.is_active = TRUE;
```

사용 예시:
```sql
-- 특정 가족의 전체 상태 조회
SELECT * FROM family_dashboard WHERE family_id = 1;
```

웹사이트에서 호출:
```javascript
const { data } = await supabase
    .from('family_dashboard')
    .select('*')
    .eq('family_id', familyId);
```

### 10-3. API 캐시 설정

```
Supabase Dashboard → Project Settings → API → Enable API Cache
```

동일 쿼리 반복 호출 시 캐시에서 즉시 반환 (대시보드 새로고침 등)

### 10-4. RPC 함수 (스캔 누락 체크 — 가장 핵심)

```sql
-- 스캔된 태그 목록을 받아서 누락 소지품을 한 번에 반환
-- Lambda에서 이 함수 1번만 호출하면 끝
CREATE OR REPLACE FUNCTION check_missing_items(
    p_device_id BIGINT,
    p_tag_uids TEXT[]
)
RETURNS TABLE (
    member_id BIGINT,
    member_name TEXT,
    member_email TEXT,
    missing_item TEXT
) AS $$
    SELECT
        fm.id,
        fm.name::TEXT,
        fm.email::TEXT,
        i.name::TEXT
    FROM family_members fm
    JOIN families f ON fm.family_id = f.id
    JOIN devices d ON d.family_id = f.id AND d.id = p_device_id
    JOIN items i ON i.member_id = fm.id AND i.is_active = TRUE AND i.is_required = TRUE
    JOIN tags t ON t.item_id = i.id AND t.is_active = TRUE
    WHERE t.tag_uid NOT IN (SELECT unnest(p_tag_uids));
$$ LANGUAGE sql STABLE;
```

Lambda (scan-process)에서 호출:
```python
# smartscan-inbound Lambda
result = supabase.rpc('check_missing_items', {
    'p_device_id': device_id,
    'p_tag_uids': scanned_tags  # ['tag-001', 'tag-003']
}).execute()

# result.data = [{ 'member_name': '자녀', 'member_email': '...', 'missing_item': '학용품' }]
```

> **효과:** 기존에 태그 조회 → 구성원 매핑 → 소지품 비교 → 누락 필터링을 4번 API 호출했다면,
> RPC 함수 1번으로 DB 내부에서 전부 처리. 네트워크 왕복 75% 감소.

---

## DB 구조 요약

```
auth.users (Supabase 내장)
    │
    ▼
profiles (사용자 프로필)
    │
    ├── families (가족 그룹)
    │       │
    │       ├── family_members (구성원)
    │       │       │
    │       │       ├── items (소지품)
    │       │       │       │
    │       │       │       └── tags (RFID 태그)
    │       │       │
    │       │       └── notifications (알림)
    │       │
    │       └── devices (RFID 리더기)
    │               │
    │               ├── tags (태그 등록)
    │               │
    │               └── scan_logs (스캔 이력)
```

### ON DELETE 정책

| FK | 정책 | 이유 |
|----|------|------|
| `profiles.id` | CASCADE (auth.users) | 계정 삭제 시 프로필 삭제 |
| `families.owner_id` | CASCADE | 사용자 삭제 시 가족도 삭제 |
| `family_members.family_id` | CASCADE | 가족 삭제 시 구성원도 삭제 |
| `family_members.profile_id` | SET NULL | 계정 연결 해제해도 구성원 유지 |
| `devices.family_id` | CASCADE | 가족 삭제 시 기기도 삭제 |
| `items.member_id` | CASCADE | 구성원 삭제 시 소지품도 삭제 |
| `tags.item_id` | CASCADE | 소지품 삭제 시 태그도 삭제 |
| `tags.device_id` | RESTRICT | 태그 등록된 기기 삭제 방지 |
| `scan_logs.device_id` | CASCADE | 기기 삭제 시 이력도 삭제 |
| `notifications.member_id` | CASCADE | 구성원 삭제 시 알림도 삭제 |

---

## 시스템 구조 요약

```
웹사이트 (smartscan-hub.com)
    → S3 + CloudFront (정적 호스팅)
    → Supabase Auth (회원가입/로그인)
    → FastAPI (Render: smart-scan-backend.onrender.com)
        → 소지품/태그/기기 CRUD, 가족 관리, 대시보드
        → Supabase DB 접속 (supabase-py)
    → Supabase Realtime (대시보드 실시간)

라즈베리파이 (RFID 스캔)
    → API Gateway → Lambda (smartscan-inbound)
        → Supabase: scan_logs INSERT + RPC check_missing_items
        → 누락 시 → Lambda (smartscan-outbound) → Resend 이메일

원격 알림 (부모→자녀)
    → API Gateway → Lambda (smartscan-remote) → Resend 이메일

카카오 챗봇
    → API Gateway → Lambda (smartscan-chatbot)
        → supabase-py로 DB 조회/등록
```

## 배포 구조

| 대상 | 호스팅 | 배포 방식 |
|------|--------|----------|
| Lambda 4개 | AWS | GitHub Actions (main push 자동) |
| FastAPI 백엔드 | Render | Render 자동 (main push 자동) |
| 웹사이트 | S3 + CloudFront | S3 sync + CF 무효화 |
| DB/Auth/Realtime | Supabase | 클라우드 (관리 불필요) |
