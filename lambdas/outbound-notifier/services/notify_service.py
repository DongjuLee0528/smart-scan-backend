from html import escape

from common.db import get_client
from common.email_client import send_email


def send_missing_alert(event) -> dict:
    """
    inbound-scanner Lambda에서 직접 호출(payload)로 전달받은
    누락 물건 알림을 처리한다.

    event 형식:
    {
      "missing_by_member": [
        {
          "member_id": 1,
          "member_name": "홍길동",
          "member_email": "user@example.com",
          "missing_items": ["지갑", "열쇠"]
        },
        ...
      ]
    }
    """
    # inbound-scanner Lambda에서 {'missing_by_member': [...]} 형태로 전달됨
    members = event.get('missing_by_member', [])
    if not members:
        return {"status": "skip", "message": "알림 대상 없음"}

    supabase = get_client()
    results = []

    for member in members:
        member_id = member.get('member_id')
        member_name = member.get('member_name', '회원')
        member_email = member.get('member_email')
        missing_items = member.get('missing_items', [])

        if not member_id or not missing_items or not member_email:
            results.append({
                "member_id": member_id,
                "status": "skipped",
                "reason": "이메일 또는 누락 물건 없음"
            })
            continue

        # ── 이메일 HTML 생성 (XSS 방지: HTML 이스케이프 적용) ──
        safe_name = escape(str(member_name))
        items_html = ''.join(
            [f'<li style="margin:6px 0">{escape(str(item))}</li>' for item in missing_items]
        )
        html = f"""
        <div style="font-family:sans-serif;max-width:480px;margin:auto">
          <h2 style="color:#e53e3e">&#x1F6A8; SmartScan Hub 알림</h2>
          <p><strong>{safe_name}</strong>님, 외출 시 다음 물건을 확인하세요:</p>
          <ul style="background:#fff5f5;padding:16px 24px;border-radius:8px">
            {items_html}
          </ul>
          <p style="color:#718096;font-size:13px">SmartScan Hub 자동 발송</p>
        </div>
        """

        # ── 이메일 발송 ──
        subject = "누락 물건 알림 - SmartScan Hub"
        ok = send_email([member_email], subject, html)

        status = "sent" if ok else "email_failed"
        print(f"[{status}] {member_name} ({member_email}) → {missing_items}")

        # ── notifications 테이블에 기록 (이메일 발송 결과와 무관하게 격리) ──
        title = "누락 물건 알림"
        message = f"누락 항목: {', '.join(missing_items)}"
        notification_payload = _build_notification_payload(member, title, message)

        try:
            if notification_payload is not None:
                supabase.table('notifications').insert(notification_payload).execute()
            else:
                print(
                    "알림 DB 저장 건너뜀: notifications 필수 컬럼 값이 부족합니다 "
                    f"(member_id={member_id})"
                )
        except Exception as db_err:
            print(f"알림 DB 저장 오류 (member_id={member_id}): {db_err}")

        results.append({
            "member_id": member_id,
            "status": status,
        })

    sent_count = sum(1 for r in results if r["status"] == "sent")
    return {
        "status": "ok",
        "total": len(results),
        "sent": sent_count,
        "details": results,
    }


def _build_notification_payload(member: dict, title: str, message: str) -> dict | None:
    family_id = member.get('family_id')
    sender_user_id = member.get('sender_user_id')
    recipient_user_id = member.get('recipient_user_id')

    if family_id is None or sender_user_id is None or recipient_user_id is None:
        return None

    channel = str(member.get('channel') or 'kakao').strip().lower()
    if channel not in {'kakao', 'sms'}:
        channel = 'kakao'

    return {
        "family_id": int(family_id),
        "sender_user_id": int(sender_user_id),
        "recipient_user_id": int(recipient_user_id),
        "type": "missing_alert",
        "channel": channel,
        "title": title,
        "message": message,
        "is_read": False,
    }
