from html import escape

from common.db import get_client
from common.email_client import send_email


def send_missing_alert(event) -> dict:
    """
    Processes missing item alerts received through direct invocation (payload)
    from inbound-scanner Lambda.

    Event format:
    {
      "missing_by_member": [
        {
          "member_id": 1,
          "member_name": "John Doe",
          "member_email": "user@example.com",
          "missing_items": ["wallet", "keys"]
        },
        ...
      ]
    }
    """
    # Delivered from inbound-scanner Lambda in {'missing_by_member': [...]} format
    members = event.get('missing_by_member', [])
    if not members:
        return {"status": "skip", "message": "No alert targets"}

    supabase = get_client()
    results = []

    for member in members:
        member_id = member.get('member_id')
        member_name = member.get('member_name', 'Member')
        member_email = member.get('member_email')
        missing_items = member.get('missing_items', [])

        if not member_id or not missing_items or not member_email:
            results.append({
                "member_id": member_id,
                "status": "skipped",
                "reason": "No email or missing items"
            })
            continue

        # ── Generate email HTML (XSS prevention: HTML escape applied) ──
        safe_name = escape(str(member_name))
        items_html = ''.join(
            [f'<li style="margin:6px 0">{escape(str(item))}</li>' for item in missing_items]
        )
        html = f"""
        <div style="font-family:sans-serif;max-width:480px;margin:auto">
          <h2 style="color:#e53e3e">&#x1F6A8; SmartScan Hub Alert</h2>
          <p><strong>{safe_name}</strong>, please check the following items before going out:</p>
          <ul style="background:#fff5f5;padding:16px 24px;border-radius:8px">
            {items_html}
          </ul>
          <p style="color:#718096;font-size:13px">SmartScan Hub automated delivery</p>
        </div>
        """

        # ── Email delivery ──
        subject = "Missing Items Alert - SmartScan Hub"
        ok = send_email([member_email], subject, html)

        status = "sent" if ok else "email_failed"
        print(f"[{status}] {member_name} ({member_email}) → {missing_items}")

        # ── Record in notifications table (isolated from email delivery result) ──
        title = "Missing Items Alert"
        message = f"Missing items: {', '.join(missing_items)}"
        notification_payload = _build_notification_payload(member, title, message)

        try:
            if notification_payload is not None:
                supabase.table('notifications').insert(notification_payload).execute()
            else:
                print(
                    "Skipping alert DB storage: missing required notifications column values "
                    f"(member_id={member_id})"
                )
        except Exception as db_err:
            print(f"Alert DB storage error (member_id={member_id}): {db_err}")

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
