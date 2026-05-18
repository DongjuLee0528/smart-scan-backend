# signup-email-verification Planning Document

> **Summary**: Connect missing email verification UI on signup page with existing backend endpoints to restore signup flow.
>
> **Project**: smart-scan-backend (SmartScan Hub IoT)
> **Version**: 1.0.0
> **Author**: hwchanyoung
> **Date**: 2026-04-20
> **Status**: Implemented (retroactive plan)

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | Backend `auth_service.register()` requires email verification records as mandatory, but verification UI has never been implemented in `signup.html`, causing all signups to fail with "Email verification must be completed before registration" error. |
| **Solution** | Add inline "Get Verification Code" button + 6-digit code input + "Confirm" button to `signup.html`. Reuse existing `smartscanApi.sendVerificationEmail` / `verifyEmail` helpers. 60-second cooldown and disable `Sign Up` button until verification complete. |
| **Function/UX Effect** | Users can complete email verification within signup form without navigating to separate pages. Verification status provides visual feedback (check icon, email field lock) ensuring UX clarity. |
| **Core Value** | Frontend↔Backend contract restoration — fixes broken link in signup funnel to enable service onboarding. |

---

## Context Anchor

> Auto-generated from Executive Summary. Propagated to Design/Do documents for context continuity.

| Key | Value |
|-----|-------|
| **WHY** | Backend requires email verification as mandatory but frontend provides no UI to call verification APIs, causing all new signups to fail |
| **WHO** | All users attempting new registration on SmartScan Hub website |
| **RISK** | (1) Email not sent when Resend free quota exhausted (2) Code brute-force attacks — vulnerable if backend has no rate limits (3) Conflicts with existing Kakao magic-link flow |
| **SUCCESS** | (1) End-to-end signup success with naver.com email (2) All 3 steps (6-digit code input→confirm→signup) proceed without errors (3) Signup button disabled when verification incomplete (4) CI passes + PR merge |
| **SCOPE** | Phase 1 (implementation complete): signup.html UI + connect existing api.js helpers. Phase 2 (separate): rate limit, resend restrictions, i18n error message improvements |

---

## 1. Overview

### 1.1 Purpose

Implement UI on SmartScan Hub website's signup page (`/signup.html`) to enable completion of email verification step. Connect previously implemented but unconnected backend endpoints (`POST /api/auth/send-verification-email`, `POST /api/auth/verify-email`) from the frontend.

### 1.2 Background

- 2026-04-03 `6b9cd50` commit: Team member added mandatory email verification check to backend `auth_service.register()`.
- 2026-04-18 `e564732` A-full refactor added `sendVerificationEmail` / `verifyEmail` helpers to `frontend/assets/api.js`.
- However, UI to call these helpers from `signup.html` was never implemented, leaving all web new signups failing since 4/3.
- 2026-04-20 bug report: User confirmed "Email verification must be completed before registration" error.

### 1.3 Related Documents

- Backend endpoints: `backend/routes/auth_route.py` (line 45, 77)
- Related commits:
  - `6b9cd50` feat: add user registration with email verification
  - `e564732` feat(auth): Kakao magic-link integration + web auth frontend
  - `be6270c` feat(signup): wire email verification flow to backend endpoints ← Implementation commit for this Plan

---

## 2. Scope

### 2.1 In Scope

- [x] Add "Get Verification Code" button to `frontend/signup.html`
- [x] Add 6-digit number input field + "Confirm" button (shown after code sending)
- [x] 60-second cooldown countdown UI
- [x] Lock email field on verification success (readOnly + gray background) + check icon
- [x] Disable `Sign Up` button before verification complete + guidance text
- [x] Reuse existing `smartscanApi.sendVerificationEmail` / `verifyEmail` helpers
- [x] Reuse existing error banner (`#signup-error`) / success banner (`#signup-success`)

### 2.2 Out of Scope

- Add backend rate limit (separate ticket)
- Resend count restrictions (client cooldown 1 per second only, no server-side limits)
- i18n error message localization (currently displays English original as-is)
- Kakao magic-link flow improvements (separate feature)
- Auto-login after signup success (maintain existing behavior)

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | Call `POST /api/auth/send-verification-email` when clicking "Get Verification Code" after email input | High | ✅ Done |
| FR-02 | Show 6-digit code input field + "Confirm" button on sending success | High | ✅ Done |
| FR-03 | "Get Verification Code" button shows "Resend (Ns)" and disabled for 60 seconds after click | High | ✅ Done |
| FR-04 | Call `POST /api/auth/verify-email` when clicking "Confirm" | High | ✅ Done |
| FR-05 | Lock email field, show check icon, enable signup button on verification success | High | ✅ Done |
| FR-06 | Disable signup button with `disabled`, show guidance text when verification incomplete | High | ✅ Done |
| FR-07 | Show red error text + allow retry on verification failure | Medium | ✅ Done |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| Performance | Email sending API response < 3 seconds | Browser Network tab |
| Security | 6-digit code client regex validation (`/^\d{6}$/`) | Manual testing |
| UX | Visual feedback for all state changes (loading, success, error) | UI testing |
| Accessibility | Maintain existing Tailwind form conventions, no `aria-` attribute changes | DevTools verification |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [x] All FR implementation complete
- [x] Local `signup.html` manual test passed (not performed — testing planned after deployment)
- [x] PR #29 created and awaiting CI pass
- [ ] Main merge + S3 + CloudFront invalidation redeployment
- [ ] Production environment end-to-end test success with real email

### 4.2 Quality Criteria

- [x] Maintain existing Tailwind design tokens (brand `#034EA2`, dark mode variants)
- [x] Maintain existing JavaScript structure (`smartscanApi` namespace)
- [x] Minimize HTML structure changes (163 lines added, 12 lines modified)
- [ ] Confirm no backend Lambda modifications needed (reuse existing logic)

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Resend(`noreply@devnavi.kr`) email quota exhaustion | High | Low | Monitor Resend dashboard, upgrade to paid plan if needed |
| Code brute-force attack (6 digits = 1 million combinations) | High | Medium | Handle backend rate limit in separate ticket (currently out of scope) |
| State conflicts with Kakao magic-link flow | Medium | Low | signup.html is isolated as independent from Kakao flow |
| Email classified as spam | Medium | Medium | Check sender domain DKIM/SPF (separate task) |
| New signup.html deployment delay due to CloudFront cache | Low | High | Force invalidation `/signup.html` on deployment |

---

## 6. Impact Analysis

### 6.1 Changed Resources

| Resource | Type | Change Description |
|----------|------|--------------------|
| `frontend/signup.html` | Static HTML/JS | Add email verification UI (buttons, inputs, state management) |
| `frontend/assets/api.js` | JS module | (No changes — reuse existing functions only) |
| `backend/services/auth_service.py` | Python service | (No changes — utilize existing logic) |
| `backend/routes/auth_route.py` | FastAPI router | (No changes — utilize existing endpoints) |

### 6.2 Current Consumers

| Resource | Operation | Code Path | Impact |
|----------|-----------|-----------|--------|
| `/api/auth/send-verification-email` | POST | `signup.html` (NEW) | Needs verification — first frontend call |
| `/api/auth/verify-email` | POST | `signup.html` (NEW) | Needs verification — first frontend call |
| `/api/auth/register` | POST | `signup.html` (existing) | None — no signature changes |
| `smartscanApi.sendVerificationEmail` | call | `signup.html` (NEW) | None — reuse existing helper |
| `smartscanApi.verifyEmail` | call | `signup.html` (NEW) | None — reuse existing helper |

### 6.3 Verification

- [x] All consumer review complete
- [x] No auth/permission changes (unauthenticated endpoints)
- [ ] No field additions/removals (confirm after deployment)

---

## 7. Architecture Considerations

### 7.1 Project Level Selection

| Level | Characteristics | Recommended For | Selected |
|-------|-----------------|-----------------|:--------:|
| **Starter** | Simple structure | Static sites | ☐ |
| **Dynamic** | Feature-based modules, BaaS | Web apps with backend | ☑ |
| **Enterprise** | Strict layer separation | High-traffic, microservices | ☐ |

SmartScan Hub is Dynamic level (FastAPI + S3 static frontend + Lambda).

### 7.2 Key Architectural Decisions

| Decision | Options | Selected | Rationale |
|----------|---------|----------|-----------|
| Framework | Next.js / Vanilla HTML | Vanilla HTML | Existing project convention |
| State Management | global / component | Module scope variables | Signup page dedicated state, low complexity |
| API Client | fetch / axios | `smartscanApi` (apiFetch wrapper) | Reuse existing code |
| Form Handling | react-hook-form / native | native FormData | Maintain existing signup structure |
| Styling | Tailwind | Tailwind | Maintain existing CDN-based |
| Testing | Manual | Manual | Static HTML, manual browser testing |

### 7.3 Clean Architecture Approach

```
Selected Level: Dynamic

Folder Structure:
frontend/
├── signup.html          ← Target of changes for this Plan
├── assets/
│   ├── api.js           ← smartscanApi helpers (existing)
│   └── layout.js        ← (unrelated)
backend/
├── routes/auth_route.py ← Endpoints (existing)
└── services/auth_service.py ← Business logic (existing)
```

---

## 8. Convention Prerequisites

### 8.1 Existing Project Conventions

- [x] Project CLAUDE.md exists (graphify rules)
- [x] Backend Python: FastAPI + SQLAlchemy convention
- [x] Frontend: Tailwind CDN + vanilla JS convention
- [x] Commit message: `<type>(<scope>): <desc>` (validate-commit.py hook enforced)

### 8.2 Conventions to Define/Verify

| Category | Current State | To Define | Priority |
|----------|---------------|-----------|:--------:|
| Naming | exists (camelCase JS, kebab-case HTML id) | Maintain | - |
| Error handling | `try/catch` + `#signup-error` banner | Maintain | - |
| API calls | `smartscanApi.*` namespace | Maintain | - |

### 8.3 Environment Variables Needed

| Variable | Purpose | Scope | Needed |
|----------|---------|-------|:------:|
| `RESEND_API_KEY` | Email sending | Server (Lambda) | ✅ Existing |
| `SMARTSCAN_API_BASE` | API base URL | Client | ✅ Existing |

No new environment variables.

---

## 9. Next Steps

1. [x] Agent 2 completed `signup.html` implementation
2. [x] PR #29 created
3. [ ] `/pdca design signup-email-verification` — Review 3 design options (retroactive)
4. [ ] Confirm CI pass then main merge
5. [ ] S3 deployment + CloudFront invalidation
6. [ ] Production environment end-to-end testing (naver.com / gmail.com)
7. [ ] `/pdca analyze signup-email-verification` — Gap verification
8. [ ] `/pdca report signup-email-verification` — Completion report

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-20 | Initial draft (retroactive plan after implementation) | hwchanyoung |
