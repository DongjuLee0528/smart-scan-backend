-- 2026-04-18 챗봇 pending 아이템 지원
-- 변경:
--   1) items.tag_uid NOT NULL → NULL (챗봇에서 이름만 추가된 아이템은 태그 미연결)
--   2) items.is_pending BOOLEAN NOT NULL DEFAULT FALSE 추가
--   3) 데이터 무결성: is_pending=FALSE 인 아이템은 tag_uid 필수 (CHECK constraint)
-- 전제: items 테이블은 현재 비어 있음 (0 rows) 확인됨 → 비파괴 마이그레이션.

BEGIN;

ALTER TABLE items
  ALTER COLUMN tag_uid DROP NOT NULL;

ALTER TABLE items
  ADD COLUMN IF NOT EXISTS is_pending BOOLEAN NOT NULL DEFAULT FALSE;

-- is_pending=FALSE 이면 tag_uid 필수. is_pending=TRUE 이면 tag_uid NULL 허용.
ALTER TABLE items
  ADD CONSTRAINT items_pending_tag_uid_check
  CHECK (is_pending = TRUE OR tag_uid IS NOT NULL);

CREATE INDEX IF NOT EXISTS ix_items_is_pending_user_device
  ON items (user_device_id, is_pending)
  WHERE is_active = TRUE;

COMMIT;
