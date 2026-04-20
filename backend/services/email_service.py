import smtplib
from datetime import datetime
from email.message import EmailMessage
from backend.common.config import settings
from backend.common.exceptions import CustomException


class EmailService:
    """
    이메일 발송 서비스

    SMTP를 통한 이메일 인증 코드 발송을 담당한다.
    회원가입 시 이메일 인증을 위해 사용되며, 설정된 SMTP 서버를 통해 메일을 발송한다.

    설계 의도:
    - 인증 코드 안전 전송: 가입 시 이메일 소유권 검증
    - 환경변수 기반 설정: 개발/운영 환경별 SMTP 서버 분리
    - 오류 처리: SMTP 연결 실패 시 적절한 예외 발생
    """
    def __init__(self) -> None:
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_use_tls = settings.SMTP_USE_TLS
        self.smtp_use_ssl = settings.SMTP_USE_SSL or self.smtp_port == 465
        self.from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
        self.from_name = settings.SMTP_FROM_NAME

    def send_verification_code(self, to_email: str, code: str, expires_at: datetime) -> None:
        """
        이메일 인증 코드 발송

        지정된 이메일 주소로 6자리 인증 코드를 발송한다.
        SSL 또는 TLS를 사용한 보안 연결을 통해 메일을 전송한다.

        Args:
            to_email: 인증 코드를 받을 이메일 주소
            code: 발송할 6자리 인증 코드
            expires_at: 인증 코드 만료 시간

        Raises:
            CustomException: SMTP 설정이 누락된 경우
            smtplib.SMTPException: 메일 발송 실패 시
        """
        if not all([self.smtp_host, self.smtp_username, self.smtp_password, self.from_email]):
            raise CustomException(500, "SMTP settings are not configured")

        message = EmailMessage()
        message["Subject"] = "[Smart Scan] Email Verification Code"
        message["From"] = f"{self.from_name} <{self.from_email}>"
        message["To"] = to_email
        message.set_content(
            "\n".join(
                [
                    "Smart Scan email verification",
                    "",
                    f"Verification code: {code}",
                    f"Expires at: {expires_at.isoformat()}",
                ]
            )
        )

        if self.smtp_use_ssl:
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(message)
            return

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            if self.smtp_use_tls:
                server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(message)

    def send_invitation_email(
        self,
        to_email: str,
        inviter_name: str,
        family_name: str,
        token: str,
        expires_at: datetime,
    ) -> None:
        """
        가족 초대 이메일 발송

        초대 링크와 만료 시각을 포함한 plain text + HTML 이메일을 발송한다.

        Args:
            to_email: 초대 대상 이메일 주소
            inviter_name: 초대를 발송한 사용자 이름
            family_name: 초대된 가족 그룹 이름
            token: 초대 UUID 문자열
            expires_at: 초대 만료 시각 (UTC)

        Raises:
            CustomException: SMTP 설정이 누락된 경우
            smtplib.SMTPException: 메일 발송 실패 시
        """
        if not all([self.smtp_host, self.smtp_username, self.smtp_password, self.from_email]):
            raise CustomException(500, "SMTP settings are not configured")

        invite_url = f"https://smartscan-hub.com/invite-accept.html?token={token}"
        subject = f"[Smart Scan] {inviter_name}님이 가족 초대를 보냈습니다"

        plain_text = "\n".join([
            f"{inviter_name}님이 '{family_name}' 가족 그룹에 초대하셨습니다.",
            "",
            "아래 링크에서 초대를 확인하세요 (7일 후 만료):",
            invite_url,
            "",
            f"만료일: {expires_at.isoformat()}",
        ])

        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #4A90E2;">Smart Scan 가족 초대</h2>
            <p><strong>{inviter_name}</strong>님이 <strong>'{family_name}'</strong> 가족 그룹에 초대하셨습니다.</p>
            <p>아래 버튼을 클릭하여 초대를 확인하세요 (7일 후 만료).</p>
            <a href="{invite_url}"
               style="display:inline-block;padding:12px 24px;background-color:#4A90E2;
                      color:#fff;text-decoration:none;border-radius:4px;margin:16px 0;">
              초대 수락하기
            </a>
            <p style="font-size:12px;color:#999;">만료일: {expires_at.isoformat()}</p>
            <p style="font-size:12px;color:#999;">
              링크가 열리지 않으면 아래 URL을 브라우저에 붙여넣기 하세요:<br>
              {invite_url}
            </p>
          </body>
        </html>
        """

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = f"{self.from_name} <{self.from_email}>"
        message["To"] = to_email
        message.set_content(plain_text)
        message.add_alternative(html_body, subtype="html")

        if self.smtp_use_ssl:
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(message)
            return

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            if self.smtp_use_tls:
                server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(message)
