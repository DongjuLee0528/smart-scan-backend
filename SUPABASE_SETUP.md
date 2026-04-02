# SmartScan Hub - Supabase 설정 가이드

## 사전 준비
- Supabase 계정 (supabase.com)
- Resend 계정 (resend.com) - 이메일 발송용
- 팀원 초대 수락 (Owner가 초대 링크 전송)

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
-- 생성 순서: users → family_groups → family_members
--           → devices → user_devices → master_tags
--           → items → scan_logs
-- ============================================================

-- 1. users
CREATE TABLE users (
    id               SERIAL PRIMARY KEY,
    kakao_user_id    VARCHAR(255) UNIQUE,
    name             VARCHAR(255) NOT NULL,
    email            VARCHAR(255) UNIQUE NOT NULL,
    phone            VARCHAR(50),
    age              INTEGER,
    role             VARCHAR(50) NOT NULL DEFAULT 'member'
                         CHECK (role IN ('owner', 'member')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. family_groups
CREATE TABLE family_groups (
    id             SERIAL PRIMARY KEY,
    group_name     VARCHAR(255) NOT NULL,
    owner_user_id  INTEGER NOT NULL
                       REFERENCES users(id) ON DELETE CASCADE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. family_members
CREATE TABLE family_members (
    id         SERIAL PRIMARY KEY,
    group_id   INTEGER NOT NULL
                   REFERENCES family_groups(id) ON DELETE CASCADE,
    user_id    INTEGER NOT NULL
                   REFERENCES users(id) ON DELETE CASCADE,
    role       VARCHAR(50) NOT NULL DEFAULT 'member'
                   CHECK (role IN ('owner', 'member')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_family_members_group_user UNIQUE (group_id, user_id)
);

-- 4. devices
CREATE TABLE devices (
    id             SERIAL PRIMARY KEY,
    serial_number  VARCHAR(255) UNIQUE NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. user_devices
CREATE TABLE user_devices (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL
                   REFERENCES users(id) ON DELETE CASCADE,
    device_id  INTEGER NOT NULL
                   REFERENCES devices(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. master_tags
CREATE TABLE master_tags (
    id         SERIAL PRIMARY KEY,
    tag_uid    VARCHAR(255) UNIQUE NOT NULL,
    label_id   VARCHAR(255) NOT NULL,
    device_id  INTEGER NOT NULL
                   REFERENCES devices(id) ON DELETE RESTRICT
);

-- 7. items
CREATE TABLE items (
    id             SERIAL PRIMARY KEY,
    name           VARCHAR(255) NOT NULL,
    user_device_id INTEGER NOT NULL
                       REFERENCES user_devices(id) ON DELETE CASCADE,
    tag_uid        VARCHAR(255) NOT NULL
                       REFERENCES master_tags(tag_uid) ON DELETE RESTRICT,
    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8. scan_logs
CREATE TABLE scan_logs (
    id             SERIAL PRIMARY KEY,
    user_device_id INTEGER NOT NULL
                       REFERENCES user_devices(id) ON DELETE CASCADE,
    item_id        INTEGER
                       REFERENCES items(id) ON DELETE SET NULL,
    status         VARCHAR(50) NOT NULL
                       CHECK (status IN ('present', 'missing')),
    scanned_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 인덱스
-- ============================================================
CREATE INDEX idx_family_groups_owner_user_id  ON family_groups(owner_user_id);
CREATE INDEX idx_family_members_group_id      ON family_members(group_id);
CREATE INDEX idx_family_members_user_id       ON family_members(user_id);
CREATE INDEX idx_user_devices_user_id         ON user_devices(user_id);
CREATE INDEX idx_user_devices_device_id       ON user_devices(device_id);
CREATE INDEX idx_master_tags_device_id        ON master_tags(device_id);
CREATE INDEX idx_items_user_device_id         ON items(user_device_id);
CREATE INDEX idx_items_tag_uid                ON items(tag_uid);
CREATE INDEX idx_items_is_active              ON items(is_active);
CREATE INDEX idx_scan_logs_user_device_id     ON scan_logs(user_device_id);
CREATE INDEX idx_scan_logs_item_id            ON scan_logs(item_id);
CREATE INDEX idx_scan_logs_status             ON scan_logs(status);
CREATE INDEX idx_scan_logs_scanned_at         ON scan_logs(scanned_at DESC);
```

---

## Step 3. RLS (보안 정책) 설정

SQL Editor → New Query → 아래 SQL 실행

```sql
-- 모든 테이블 RLS 활성화
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE family_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE family_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE master_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE items ENABLE ROW LEVEL SECURITY;
ALTER TABLE scan_logs ENABLE ROW LEVEL SECURITY;

-- users: 본인 데이터만 조회
CREATE POLICY "본인만 조회" ON users
    FOR SELECT USING (auth.uid()::text = kakao_user_id);

CREATE POLICY "본인만 수정" ON users
    FOR UPDATE USING (auth.uid()::text = kakao_user_id);

-- family_groups: 본인이 owner인 그룹만 조회
CREATE POLICY "그룹 조회" ON family_groups
    FOR SELECT USING (
        owner_user_id IN (
            SELECT id FROM users WHERE kakao_user_id = auth.uid()::text
        )
    );

-- family_members: 같은 그룹 구성원만 조회
CREATE POLICY "구성원 조회" ON family_members
    FOR SELECT USING (
        group_id IN (
            SELECT group_id FROM family_members fm
            JOIN users u ON fm.user_id = u.id
            WHERE u.kakao_user_id = auth.uid()::text
        )
    );
```

---

## Step 4. Auth 설정

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

## Step 5. 환경변수 수집

```
Project Settings → API
```

아래 값을 팀 채널에 공유:

| 변수명 | 위치 |
|--------|------|
| `SUPABASE_URL` | Project URL |
| `SUPABASE_ANON_KEY` | anon public |
| `SUPABASE_SERVICE_KEY` | service_role (Lambda 서버용) |

---

## Step 6. 백엔드 연동 (FastAPI)

`backend/common/config.py`에 추가:

```python
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
```

---

## Step 7. Lambda 환경변수 추가

AWS Lambda → smartscan-outbound → 구성 → 환경 변수:

| 키 | 값 |
|----|-----|
| `RESEND_API_KEY` | Resend API Key |
| `NOTIFY_EMAILS` | 수신자 이메일 (쉼표 구분, 예: a@gmail.com,b@gmail.com) |
| `SUPABASE_URL` | Supabase Project URL |
| `SUPABASE_ANON_KEY` | Supabase anon key |

---

## DB 구조 요약

```
users
├── family_groups (owner)
│   └── family_members (구성원 목록)
└── user_devices (디바이스 연결)
    ├── items (소지품 태그)
    │   └── master_tags (RFID 태그 UID)
    └── scan_logs (스캔 이력)

devices
└── master_tags
```

### ON DELETE 정책

| FK | 정책 | 이유 |
|----|------|------|
| `family_groups.owner_user_id` | CASCADE | 유저 삭제 시 그룹도 삭제 |
| `family_members.group_id` | CASCADE | 그룹 삭제 시 멤버십도 삭제 |
| `user_devices` | CASCADE | 유저/디바이스 삭제 시 연결 삭제 |
| `items.tag_uid` | RESTRICT | 아이템 연결된 태그 삭제 방지 |
| `scan_logs.item_id` | SET NULL | 아이템 삭제돼도 이력 보존 |
| `master_tags.device_id` | RESTRICT | 태그 있는 디바이스 삭제 방지 |
