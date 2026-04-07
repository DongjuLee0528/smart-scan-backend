import os
import resend


def send_email(to: list, subject: str, html: str) -> bool:
    resend.api_key = os.environ.get('RESEND_API_KEY')
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
