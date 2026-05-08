import os
import resend

def send_email(to: list, subject: str, html: str) -> bool:
    api_key = os.environ.get('RESEND_API_KEY')
    if not api_key:
        print("이메일 발송 오류: RESEND_API_KEY 환경변수가 설정되지 않았습니다")
        return False
    resend.api_key = api_key
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