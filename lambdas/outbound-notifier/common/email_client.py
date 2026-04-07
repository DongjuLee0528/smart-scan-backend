import os
import resend

_api_key = os.environ.get('RESEND_API_KEY')
if not _api_key:
    raise ValueError("RESEND_API_KEY must be set")
resend.api_key = _api_key


def send_email(to: list, subject: str, html: str) -> bool:
    try:
        resend.Emails.send({
            "from": "SmartScan Hub <noreply@smartscan-hub.com>",
            "to": to,
            "subject": subject,
            "html": html,
        })
        return True
    except Exception as e:
        print(f"이메일 발송 오류: {e}")
        return False
