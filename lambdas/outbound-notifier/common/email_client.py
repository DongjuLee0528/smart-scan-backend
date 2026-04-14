"""
이메일 전송 클라이언트 (Resend API)

Resend 서비스를 이용하여 누락된 소지품 알림 이메일을 발송하는 클라이언트입니다.
전송 오류 발생 시 자동으로 로그를 생성하여 디버깅을 지원합니다.

환경변수:
- RESEND_API_KEY: Resend API 키 (필수)

전송 설정:
- 발송자: SmartScan Hub <noreply@smartscan-hub.com>
- 도메인: smartscan-hub.com (발송 인증 된 도메인)

사용 예: send_email(['user@example.com'], '제목', '<html>내용</html>')
"""

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
