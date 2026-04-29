import smtplib
from datetime import datetime
from email.message import EmailMessage
from backend.common.config import settings
from backend.common.exceptions import CustomException


class EmailService:
    """
    Email sending service

    Handles sending email verification codes through SMTP.
    Used for email verification during registration, sends emails through configured SMTP server.

    Design principles:
    - Safe verification code transmission: Email ownership verification during registration
    - Environment variable-based configuration: Separate SMTP servers for dev/prod environments
    - Error handling: Raise appropriate exceptions when SMTP connection fails
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
        Send email verification code

        Send 6-digit verification code to specified email address.
        Send email through secure connection using SSL or TLS.

        Args:
            to_email: Email address to receive verification code
            code: 6-digit verification code to send
            expires_at: Verification code expiration time

        Raises:
            CustomException: When SMTP settings are missing
            smtplib.SMTPException: When email sending fails
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

    def send_alert_email(
        self,
        to_email: str,
        sender_name: str,
        title: str,
        message: str,
    ) -> None:
        """Send manual alert email (for remote alert feature)"""
        if not all([self.smtp_host, self.smtp_username, self.smtp_password, self.from_email]):
            raise CustomException(500, "SMTP settings are not configured")

        plain_text = "\n".join([
            f"SmartScan Hub alert from {sender_name} has arrived.",
            "",
            f"Subject: {title}",
            f"Message: {message}",
        ])
        html_body = f"""
        <html>
          <body style="font-family:Arial,sans-serif;color:#333;">
            <h2 style="color:#034EA2;">SmartScan Hub Alert</h2>
            <p>Alert from <strong>{sender_name}</strong> has arrived.</p>
            <div style="background:#f8fafc;border-left:4px solid #034EA2;
                        padding:12px 16px;margin:16px 0;border-radius:4px;">
              <p style="font-weight:600;margin:0 0 8px;">{title}</p>
              <p style="margin:0;">{message}</p>
            </div>
          </body>
        </html>
        """

        msg = EmailMessage()
        msg["Subject"] = f"[SmartScan] {title}"
        msg["From"] = f"{self.from_name} <{self.from_email}>"
        msg["To"] = to_email
        msg.set_content(plain_text)
        msg.add_alternative(html_body, subtype="html")

        if self.smtp_use_ssl:
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            return

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            if self.smtp_use_tls:
                server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)

    def send_invitation_email(
        self,
        to_email: str,
        inviter_name: str,
        family_name: str,
        token: str,
        expires_at: datetime,
    ) -> None:
        """
        Send family invitation email

        Send plain text + HTML email including invitation link and expiration time.

        Args:
            to_email: Target email address for invitation
            inviter_name: Name of user who sent invitation
            family_name: Name of invited family group
            token: Invitation UUID string
            expires_at: Invitation expiration time (UTC)

        Raises:
            CustomException: When SMTP settings are missing
            smtplib.SMTPException: When email sending fails
        """
        if not all([self.smtp_host, self.smtp_username, self.smtp_password, self.from_email]):
            raise CustomException(500, "SMTP settings are not configured")

        invite_url = f"https://smartscan-hub.com/invite-accept.html?token={token}"
        subject = f"[Smart Scan] {inviter_name} sent you a family invitation"

        plain_text = "\n".join([
            f"{inviter_name} has invited you to '{family_name}' family group.",
            "",
            "Please check the invitation at the link below (expires after 7 days):",
            invite_url,
            "",
            f"Expires: {expires_at.isoformat()}",
        ])

        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #4A90E2;">Smart Scan Family Invitation</h2>
            <p><strong>{inviter_name}</strong> has invited you to <strong>'{family_name}'</strong> family group.</p>
            <p>Please click the button below to check the invitation (expires after 7 days).</p>
            <a href="{invite_url}"
               style="display:inline-block;padding:12px 24px;background-color:#4A90E2;
                      color:#fff;text-decoration:none;border-radius:4px;margin:16px 0;">
              Accept Invitation
            </a>
            <p style="font-size:12px;color:#999;">Expires: {expires_at.isoformat()}</p>
            <p style="font-size:12px;color:#999;">
              If the link doesn't open, please copy and paste the URL below into your browser:<br>
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
