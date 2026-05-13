# Family Invitations — Plan

## Executive Summary

| Perspective | Content |
|---|---|
| Problem | When Admin tries to add existing users (`hwchanyung@gmail.com` etc.) as family members, returns "User already belongs to another family" 409. This is due to design constraint where all users are automatically registered as owner of their own family upon signup. |
| Solution | Introduce invitation-based flow: Admin sends email invitation → recipient clicks link → confirms identity then leaves current family and joins invited family. |
| Function UX Effect | "Add Member" changes to "Invite Member". Recipients decide to join via accept link in email. Cases where user is owner with other members are blocked in MVP. |
| Core Value | Multi-family transitions are safe and explicit. Family membership movement becomes possible while maintaining existing 1:N (user-family) constraint. |

## Context Anchor

| Key | Value |
|---|---|
| WHY | Current design has no way to join another family. All registered users are locked as their own family owner. |
| WHO | Family owner(Admin, inviter) + invited existing user(recipient) |
| RISK | Orphaned family occurs when owner leaves while leaving other members. Blocked in MVP. |
| SUCCESS | Admin invites → recipient accepts → recipient joins new family as member. Leaves existing family. |
| SCOPE | Invitation table/CRUD + email sending + accept page + UI refactoring. Ownership transfer is out of scope. |

## Requirements

### FR-01 Create Invitation (Admin)
- Admin creates invitation with name, email, phone_number, age
- Validation: 409 if user with corresponding email/phone combination in `users` is already a member of the same family
- Scenarios:
  - Already member of **different** family: Normal — only create invitation (handle withdrawal at acceptance time)
  - Unregistered email: Normal — recipient follows email link → signup → login then accept
- Token: UUID v4, `expires_at = now + 7d`, status = `pending`

### FR-02 Send Invitation Email
- Sender: `SmartScan Hub <noreply@devnavi.kr>` (Resend SMTP)
- Link: `https://smartscan-hub.com/invite-accept.html?token={TOKEN}`
- Content: Inviter name, family name, accept/expiration notice

### FR-03 Retrieve Invitation (Public by token)
- `GET /api/family-invitations/by-token/{token}` — No authentication required
- Response: family_name, inviter_name, invitee_email, status, expires_at
- Returns expired/accepted/cancelled status as-is (frontend handles branching)

### FR-04 Accept Invitation (Auth required)
- `POST /api/family-invitations/{token}/accept`
- Conditions:
  - Currently logged in user's email === invitation.email (match validation)
  - invitation.status === pending AND not expired
  - If user is owner of current family and **other members besides self exist**, return 409 `"Transfer ownership or dissolve current family first"`
  - If user already belongs to target family, return 409
- Transaction:
  1. Delete current family_member
  2. Check remaining member count of current family → if 0, delete family (+cascade: items, devices…)
  3. Create new family_member (role=member)
  4. invitation.status = accepted, accepted_at = now

### FR-05 Decline Invitation (Auth required)
- `POST /api/family-invitations/{token}/decline`
- invitation.status = declined

### FR-06 Cancel Invitation (Admin)
- `DELETE /api/family-invitations/{id}` — Admin only, can only cancel pending invitations

### FR-07 List Invitations (Admin)
- `GET /api/family-invitations` — List of pending invitations for own family

### FR-08 UI
- `members.html`: "Add Member" modal → Change text to "Send Invitation" + add pending invitations table section (cancel button)
- `invite-accept.html` (new): Retrieve invitation by token → family info + accept/decline buttons → redirect to login.html if not logged in (`?redirect=/invite-accept.html?token=...`)

## Risks & Mitigation

| Risk | Mitigation |
|---|---|
| Owner leaves family alone → orphaned family | Block accept if owner with other members exists |
| User A hijacks another person's token | Validate `current_user.email === invitation.email` on accept |
| Duplicate invitations to same email | Don't recreate if existing pending invitation exists, update instead (or 409) — MVP returns 409 |
| Email sending fails leaving only invitation record | Rollback transaction on email sending failure |

## Non-Goals (MVP Exclusions)
- Ownership transfer (separate feature)
- Invitation via phone/SMS
- Bulk invitation
- Re-invite UX (cancel then recreate)

## Impact

- **New files**: `backend/models/family_invitation.py`, `backend/repositories/family_invitation_repository.py`, `backend/services/family_invitation_service.py`, `backend/routes/family_invitation_route.py`, `backend/schemas/family_invitation_schema.py`, `frontend/invite-accept.html`
- **Modified files**: `backend/app.py` (route include), `backend/services/family_member_service.py` (maintain add_member but change internal call to invitation creation or establish separate route), `frontend/members.html`, `frontend/assets/api.js`
- **DB Migration**: Create `family_invitations` table (manual Supabase SQL execution)
