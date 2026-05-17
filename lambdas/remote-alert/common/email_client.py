"""
Email client wrapper for remote-alert Lambda function

Provides email sending functionality by importing from shared Lambda module.
Used for sending alert notifications to users via Resend email service.
"""

from lambda_shared.email_client import send_email
