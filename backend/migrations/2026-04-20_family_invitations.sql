-- Migration: family_invitations 테이블 생성
-- Created: 2026-04-20
-- Description: 가족 초대 시스템을 위한 테이블 및 인덱스 추가

CREATE TABLE IF NOT EXISTS family_invitations (
  id                SERIAL PRIMARY KEY,
  family_id         INTEGER NOT NULL REFERENCES families(id) ON DELETE CASCADE,
  inviter_user_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  email             VARCHAR(255) NOT NULL,
  suggested_name    VARCHAR(100),
  suggested_phone   VARCHAR(30),
  suggested_age     INTEGER,
  token             UUID NOT NULL UNIQUE,
  status            VARCHAR(20) NOT NULL DEFAULT 'pending',
  expires_at        TIMESTAMPTZ NOT NULL,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  accepted_at       TIMESTAMPTZ,
  declined_at       TIMESTAMPTZ,
  cancelled_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_family_invitations_family_email_status
  ON family_invitations(family_id, email, status);

CREATE INDEX IF NOT EXISTS idx_family_invitations_expires_at
  ON family_invitations(expires_at);
