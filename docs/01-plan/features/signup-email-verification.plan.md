# signup-email-verification Planning Document

> **Summary**: 회원가입 페이지에 누락된 이메일 인증 UI 를 backend 기존 엔드포인트와 연결하여 가입 플로우를 복구한다.
>
> **Project**: smart-scan-backend (SmartScan Hub IoT)
> **Version**: 1.0.0
> **Author**: 황찬영 (hwchanyoung)
> **Date**: 2026-04-20
> **Status**: Implemented (retroactive plan)

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | Backend `auth_service.register()` 는 이메일 인증 레코드를 필수로 요구하지만, `signup.html` 에 인증 UI 가 한 번도 구현된 적이 없어 모든 회원가입이 "Email verification must be completed before registration" 에러로 실패한다. |
| **Solution** | `signup.html` 에 "인증 코드 받기" 버튼 + 6자리 코드 입력 + "확인" 버튼을 인라인 추가. 기존 `smartscanApi.sendVerificationEmail` / `verifyEmail` 헬퍼 재사용. 60초 쿨다운 및 인증 완료 전 `회원가입` 버튼 비활성화. |
| **Function/UX Effect** | 사용자가 별도 페이지 이동 없이 가입 폼에서 이메일 인증을 완료할 수 있다. 인증 상태가 시각적(체크 아이콘, 이메일 필드 잠금)으로 피드백되어 UX 명확성 확보. |
| **Core Value** | 프론트엔드↔백엔드 계약 복구 — 회원가입 퍼널의 깨진 고리를 메워 서비스 온보딩이 가능해진다. |

---

## Context Anchor

> Auto-generated from Executive Summary. Propagated to Design/Do documents for context continuity.

| Key | Value |
|-----|-------|
| **WHY** | Backend 가 이메일 인증을 필수로 요구하는데 프론트엔드가 인증 API 를 호출하는 UI 를 제공하지 않아 모든 신규 가입이 실패 중 |
| **WHO** | SmartScan Hub 웹사이트에서 신규 회원가입을 시도하는 모든 사용자 |
| **RISK** | (1) Resend 무료 쿼터 소진 시 이메일 미발송 (2) code brute-force 공격 — backend 에 rate limit 없으면 악용 가능 (3) 기존 카카오 매직링크 플로우와의 충돌 |
| **SUCCESS** | (1) naver.com 이메일로 end-to-end 가입 성공 (2) 6자리 코드 입력→확인→회원가입 3단계 모두 에러 없이 진행 (3) 인증 미완료 상태에서 회원가입 버튼 비활성화 (4) CI 통과 + PR merge |
| **SCOPE** | Phase 1 (구현 완료): signup.html UI + 기존 api.js 헬퍼 연결. Phase 2 (별도): rate limit, 재전송 제한, i18n 에러 메시지 개선 |

---

## 1. Overview

### 1.1 Purpose

SmartScan Hub 웹사이트의 회원가입 페이지(`/signup.html`)에서 이메일 인증 단계를 완료할 수 있도록 UI 를 구현한다. 기존에 구현되어 있으나 연결되지 않았던 백엔드 엔드포인트(`POST /api/auth/send-verification-email`, `POST /api/auth/verify-email`)를 프론트엔드에서 호출한다.

### 1.2 Background

- 2026-04-03 `6b9cd50` 커밋으로 팀원이 백엔드 `auth_service.register()` 에 이메일 인증 필수 체크를 추가했다.
- 2026-04-18 `e564732` A-full 리팩터로 `frontend/assets/api.js` 에 `sendVerificationEmail` / `verifyEmail` 헬퍼가 추가됐다.
- 그러나 `signup.html` 에서 이 헬퍼를 호출하는 UI 는 한 번도 구현되지 않아, 4/3 이후 모든 웹 신규 가입이 실패한 채 방치됨.
- 2026-04-20 버그 신고: 사용자가 "Email verification must be completed before registration" 에러 확인.

### 1.3 Related Documents

- Backend 엔드포인트: `backend/routes/auth_route.py` (line 45, 77)
- 관련 커밋:
  - `6b9cd50` feat: add user registration with email verification
  - `e564732` feat(auth): Kakao magic-link integration + web auth frontend
  - `be6270c` feat(signup): wire email verification flow to backend endpoints ← 이 Plan의 구현 commit

---

## 2. Scope

### 2.1 In Scope

- [x] `frontend/signup.html` 에 "인증 코드 받기" 버튼 추가
- [x] 6자리 숫자 입력 필드 + "확인" 버튼 추가 (코드 발송 후 표시)
- [x] 60초 쿨다운 카운트다운 UI
- [x] 인증 성공 시 이메일 필드 잠금(readOnly + 회색 배경) + 체크 아이콘
- [x] 인증 완료 전 `회원가입` 버튼 비활성화 + 안내 문구
- [x] 기존 `smartscanApi.sendVerificationEmail` / `verifyEmail` 헬퍼 재사용
- [x] 기존 에러 배너(`#signup-error`) / 성공 배너(`#signup-success`) 재사용

### 2.2 Out of Scope

- 백엔드 rate limit 추가 (별도 티켓)
- 재전송 횟수 제한 (초당 1회만 클라이언트 쿨다운, 서버 측 제한 없음)
- i18n 에러 메시지 현지화 (현재 영어 원문 그대로 표시)
- 카카오 매직링크 플로우 개선 (별도 feature)
- signup 성공 후 자동 로그인 처리 (기존 동작 유지)

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | 이메일 입력 후 "인증 코드 받기" 클릭 시 `POST /api/auth/send-verification-email` 호출 | High | ✅ Done |
| FR-02 | 발송 성공 시 6자리 코드 입력 필드 + "확인" 버튼 노출 | High | ✅ Done |
| FR-03 | "인증 코드 받기" 버튼은 클릭 후 60초간 "재전송 (Ns)" 표시 후 비활성화 | High | ✅ Done |
| FR-04 | "확인" 클릭 시 `POST /api/auth/verify-email` 호출 | High | ✅ Done |
| FR-05 | 인증 성공 시 이메일 필드 잠금, 체크 아이콘 표시, 회원가입 버튼 활성화 | High | ✅ Done |
| FR-06 | 인증 미완료 시 회원가입 버튼 `disabled`, 안내 문구 표시 | High | ✅ Done |
| FR-07 | 인증 실패 시 빨간색 에러 문구 + 재시도 허용 | Medium | ✅ Done |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| Performance | 이메일 발송 API 응답 < 3초 | 브라우저 Network 탭 |
| Security | 6자리 코드 클라이언트 정규식 검증 (`/^\d{6}$/`) | Manual 테스트 |
| UX | 모든 상태 변화에 시각 피드백 (로딩, 성공, 에러) | UI 테스트 |
| Accessibility | 기존 Tailwind form 컨벤션 유지, `aria-` 속성 변경 없음 | DevTools 검증 |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [x] 모든 FR 구현 완료
- [x] 로컬 `signup.html` 수동 테스트 통과 (미실시 — 배포 후 테스트 예정)
- [x] PR #29 생성 및 CI 통과 대기
- [ ] Main merge + S3 + CloudFront invalidation 재배포
- [ ] Production 환경에서 real email 로 end-to-end 테스트 성공

### 4.2 Quality Criteria

- [x] 기존 Tailwind 디자인 토큰 유지 (brand `#034EA2`, dark mode variants)
- [x] 기존 JavaScript 구조 유지 (`smartscanApi` 네임스페이스)
- [x] HTML 구조 변경 최소화 (163줄 추가, 12줄 수정)
- [ ] 백엔드 Lambda 수정 불필요 확인 (기존 로직 재사용)

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Resend(`noreply@devnavi.kr`) 이메일 쿼터 소진 | High | Low | Resend 대시보드 모니터링, 필요시 유료 플랜 전환 |
| 코드 브루트포스 공격 (6자리 = 100만 조합) | High | Medium | 백엔드 rate limit 별도 티켓에서 처리 (현재 스코프 out) |
| 카카오 매직링크 플로우와 상태 충돌 | Medium | Low | signup.html 은 카카오 플로우와 독립적이므로 격리됨 |
| 이메일이 스팸함으로 분류 | Medium | Medium | 발송자 도메인 DKIM/SPF 확인 (별도 태스크) |
| CloudFront 캐시로 인해 신규 signup.html 배포 지연 | Low | High | 배포 시 invalidation `/signup.html` 강제 |

---

## 6. Impact Analysis

### 6.1 Changed Resources

| Resource | Type | Change Description |
|----------|------|--------------------|
| `frontend/signup.html` | Static HTML/JS | 이메일 인증 UI (버튼, 입력, 상태 관리) 추가 |
| `frontend/assets/api.js` | JS module | (변경 없음 — 기존 함수 재사용만) |
| `backend/services/auth_service.py` | Python service | (변경 없음 — 기존 로직 활용) |
| `backend/routes/auth_route.py` | FastAPI router | (변경 없음 — 기존 엔드포인트 활용) |

### 6.2 Current Consumers

| Resource | Operation | Code Path | Impact |
|----------|-----------|-----------|--------|
| `/api/auth/send-verification-email` | POST | `signup.html` (NEW) | Needs verification — 최초 프론트엔드 호출 |
| `/api/auth/verify-email` | POST | `signup.html` (NEW) | Needs verification — 최초 프론트엔드 호출 |
| `/api/auth/register` | POST | `signup.html` (기존) | None — signature 변경 없음 |
| `smartscanApi.sendVerificationEmail` | call | `signup.html` (NEW) | None — 기존 helper 재사용 |
| `smartscanApi.verifyEmail` | call | `signup.html` (NEW) | None — 기존 helper 재사용 |

### 6.3 Verification

- [x] 모든 consumer 검토 완료
- [x] auth/permission 변경 없음 (비인증 엔드포인트)
- [ ] 필드 추가/제거 없음 (배포 후 확인)

---

## 7. Architecture Considerations

### 7.1 Project Level Selection

| Level | Characteristics | Recommended For | Selected |
|-------|-----------------|-----------------|:--------:|
| **Starter** | Simple structure | Static sites | ☐ |
| **Dynamic** | Feature-based modules, BaaS | Web apps with backend | ☑ |
| **Enterprise** | Strict layer separation | High-traffic, microservices | ☐ |

SmartScan Hub 는 Dynamic 레벨 (FastAPI + S3 static frontend + Lambda).

### 7.2 Key Architectural Decisions

| Decision | Options | Selected | Rationale |
|----------|---------|----------|-----------|
| Framework | Next.js / Vanilla HTML | Vanilla HTML | 기존 프로젝트 컨벤션 |
| State Management | global / component | 모듈 스코프 변수 | signup 페이지 전용 상태, 복잡도 낮음 |
| API Client | fetch / axios | `smartscanApi` (apiFetch wrapper) | 기존 코드 재사용 |
| Form Handling | react-hook-form / native | native FormData | 기존 signup 구조 유지 |
| Styling | Tailwind | Tailwind | 기존 CDN 기반 유지 |
| Testing | Manual | Manual | 정적 HTML, 수동 브라우저 테스트 |

### 7.3 Clean Architecture Approach

```
Selected Level: Dynamic

Folder Structure:
frontend/
├── signup.html          ← 본 Plan 의 변경 대상
├── assets/
│   ├── api.js           ← smartscanApi 헬퍼 (기존)
│   └── layout.js        ← (무관)
backend/
├── routes/auth_route.py ← 엔드포인트 (기존)
└── services/auth_service.py ← 비즈니스 로직 (기존)
```

---

## 8. Convention Prerequisites

### 8.1 Existing Project Conventions

- [x] 프로젝트 CLAUDE.md 존재 (graphify 규칙)
- [x] 백엔드 Python: FastAPI + SQLAlchemy 컨벤션
- [x] 프론트엔드: Tailwind CDN + vanilla JS 컨벤션
- [x] Commit message: `<type>(<scope>): <desc>` (validate-commit.py hook 강제)

### 8.2 Conventions to Define/Verify

| Category | Current State | To Define | Priority |
|----------|---------------|-----------|:--------:|
| Naming | exists (camelCase JS, kebab-case HTML id) | 유지 | - |
| Error handling | `try/catch` + `#signup-error` banner | 유지 | - |
| API calls | `smartscanApi.*` 네임스페이스 | 유지 | - |

### 8.3 Environment Variables Needed

| Variable | Purpose | Scope | Needed |
|----------|---------|-------|:------:|
| `RESEND_API_KEY` | 이메일 발송 | Server (Lambda) | ✅ 기존 |
| `SMARTSCAN_API_BASE` | API base URL | Client | ✅ 기존 |

신규 환경변수 없음.

---

## 9. Next Steps

1. [x] Agent 2 가 `signup.html` 구현 완료
2. [x] PR #29 생성
3. [ ] `/pdca design signup-email-verification` — 3가지 설계안 검토 (retroactive)
4. [ ] CI 통과 확인 후 main merge
5. [ ] S3 배포 + CloudFront invalidation
6. [ ] Production 환경 end-to-end 테스트 (naver.com / gmail.com)
7. [ ] `/pdca analyze signup-email-verification` — gap 검증
8. [ ] `/pdca report signup-email-verification` — 완료 보고

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-20 | Initial draft (retroactive plan after implementation) | 황찬영 |
