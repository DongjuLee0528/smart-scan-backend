# Family Invitations — Plan

## Executive Summary

| 관점 | 내용 |
|---|---|
| Problem | Admin이 기존 가입자(`hwchanyung@gmail.com` 등)를 family 구성원으로 추가하려 하면 "User already belongs to another family" 409. 회원가입 시 모든 유저가 자기 family의 owner로 자동 등록되는 설계 제약 때문. |
| Solution | 초대 기반 플로우 도입: Admin이 이메일 초대 전송 → 수신자가 링크 클릭 → 본인 확인 후 현재 family 떠나고 초대받은 family에 합류. |
| Function UX Effect | "구성원 추가" = "구성원 초대"로 변경. 수신자는 메일의 수락 링크로 합류 결정. 본인 owner+다른 멤버 있는 경우는 MVP에서 차단. |
| Core Value | 다중 가족 전환이 안전하고 명시적. 기존 1:N(유저-family) 제약 유지하면서 가족 소속 이동이 가능해짐. |

## Context Anchor

| Key | Value |
|---|---|
| WHY | 현재 설계에서 다른 가족에 합류할 방법이 없음. 모든 가입자가 자기 family owner로 lock됨. |
| WHO | Family owner(Admin, 초대자) + 초대받는 기가입자(수신자) |
| RISK | owner가 다른 멤버 남겨둔 채 이탈 시 고아 family 발생. MVP에서는 차단. |
| SUCCESS | Admin이 초대 → 수신자 수락 → 수신자가 새 family에 member로 합류. 기존 family에서 탈퇴. |
| SCOPE | 초대 테이블/CRUD + 메일 발송 + 수락 페이지 + UI 리팩토링. 소유권 이전은 범위 외. |

## Requirements

### FR-01 초대 생성 (Admin)
- Admin은 name, email, phone_number, age로 초대 생성
- 검증: `users`에 해당 email/phone 조합의 유저가 이미 같은 family 멤버면 409
- 조합:
  - 이미 **다른** family 멤버: 정상 — 초대만 생성(수락 시점에 탈퇴 처리)
  - 미가입 이메일: 정상 — 수신자는 메일 링크 → signup → 로그인 후 수락
- Token: UUID v4, `expires_at = now + 7d`, status = `pending`

### FR-02 초대 메일 발송
- 발신자: `SmartScan Hub <noreply@devnavi.kr>` (Resend SMTP)
- 링크: `https://smartscan-hub.com/invite-accept.html?token={TOKEN}`
- 내용: 초대자 이름, family 이름, 수락/만료 안내

### FR-03 초대 조회 (Public by token)
- `GET /api/family-invitations/by-token/{token}` — 인증 불필요
- 응답: family_name, inviter_name, invitee_email, status, expires_at
- 만료/수락됨/취소됨 상태도 그대로 반환(프론트에서 분기)

### FR-04 초대 수락 (Auth required)
- `POST /api/family-invitations/{token}/accept`
- 조건:
  - 현재 로그인한 유저의 email === invitation.email (일치 검증)
  - invitation.status === pending AND not expired
  - 유저가 현재 family의 owner이고 **본인 외 다른 멤버가 존재**하면 409 `"Transfer ownership or dissolve current family first"`
  - 유저가 대상 family에 이미 소속이면 409
- 트랜잭션:
  1. 현재 family_member 삭제
  2. 현재 family의 남은 멤버 수 확인 → 0이면 family 삭제(+cascade: items, devices…)
  3. 새 family_member 생성(role=member)
  4. invitation.status = accepted, accepted_at = now

### FR-05 초대 거절 (Auth required)
- `POST /api/family-invitations/{token}/decline`
- invitation.status = declined

### FR-06 초대 취소 (Admin)
- `DELETE /api/family-invitations/{id}` — Admin only, pending만 취소 가능

### FR-07 초대 목록 (Admin)
- `GET /api/family-invitations` — 본인 family의 pending 초대 목록

### FR-08 UI
- `members.html`: "구성원 추가" 모달 → "초대 보내기" 텍스트 변경 + pending 초대 테이블 섹션 추가(취소 버튼)
- `invite-accept.html` (신규): 토큰으로 초대 조회 → family 정보 + 수락/거절 버튼 → 미로그인 시 login.html로 리다이렉트(`?redirect=/invite-accept.html?token=...`)

## Risks & Mitigation

| Risk | Mitigation |
|---|---|
| owner가 가족을 혼자 두고 떠남 → 고아 family | owner이면서 다른 멤버 있으면 accept 차단 |
| 유저 A가 다른 사람 토큰으로 가로채기 | accept 시 `current_user.email === invitation.email` 검증 |
| 동일 이메일에 중복 초대 | 기존 pending 초대 있으면 재생성하지 않고 갱신(또는 409) — MVP는 409 |
| 이메일 전송 실패 시 invitation 레코드만 남음 | 트랜잭션에서 메일 발송 실패 시 rollback |

## Non-Goals (MVP 제외)
- Ownership transfer (별도 기능)
- Invitation via phone/SMS
- Bulk invitation
- Re-invite UX(취소 후 새로 생성)

## Impact

- **신규 파일**: `backend/models/family_invitation.py`, `backend/repositories/family_invitation_repository.py`, `backend/services/family_invitation_service.py`, `backend/routes/family_invitation_route.py`, `backend/schemas/family_invitation_schema.py`, `frontend/invite-accept.html`
- **수정 파일**: `backend/app.py` (route include), `backend/services/family_member_service.py` (add_member 유지하되 내부에서 초대 생성 호출로 변경 or 별도 라우트 신설), `frontend/members.html`, `frontend/assets/api.js`
- **DB 마이그레이션**: `family_invitations` 테이블 생성 (Supabase SQL 수동 실행)
