from common.db import get_client
from common.email_client import send_email


def send_missing_alert(event) -> dict:
    """
    inbound-scanner Lambda에서 직접 호출(payload)로 전달받은
    누락 물건 알림을 처리한다.

    event 형식:
    [
      {
        "member_id": "uuid",
        "member_name": "홍길동",
        "member_email": "user@example.com",
        "missing_items": ["지갑", "열쇠"]
      },
      ...
    ]
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

        if not missing_items or not member_email:
            results.append({
                "member_id": member_id,
                "status": "skipped",
                "reason": "이메일 또는 누락 물건 없음"
            })
            continue

        # ── 이메일 HTML 생성 ──
        items_html = ''.join(
            [f'<li style="margin:6px 0">{item}</li>' for item in missing_items]
        )
        html = f"""
        <div style="font-family:sans-serif;max-width:480px;margin:auto">
          <h2 style="color:#e53e3e">🚨 SmartScan Hub 알림</h2>
          <p><strong>{member_name}</strong>님, 외출 시 다음 물건을 확인하세요:</p>
          <ul style="background:#fff5f5;padding:16px 24px;border-radius:8px">
            {items_html}
          </ul>
          <p style="color:#718096;font-size:13px">SmartScan Hub 자동 발송</p>
        </div>
        """

        # ── 이메일 발송 ──
        subject = "⚠️ 누락 물건 알림 - SmartScan Hub"
        ok = send_email([member_email], subject, html)

        # ── notifications 테이블에 기록 ──
        title = "누락 물건 알림"
        message = f"누락 항목: {', '.join(missing_items)}"

        try:
            supabase.table('notifications').insert({
                "member_id": member_id,
                "type": "missing",
                "title": title,
                "message": message,
                "sent_via": "email",
            }).execute()
        except Exception as e:
            print(f"알림 DB 저장 오류 (member_id={member_id}): {e}")

        status = "sent" if ok else "email_failed"
        print(f"[{status}] {member_name} ({member_email}) → {missing_items}")
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
