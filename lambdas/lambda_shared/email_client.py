"""
Email Client for Lambda Functions

Provides email sending functionality using Resend API for Lambda functions.
Used for sending missing item alerts and notifications.
"""

import os
import resend


def send_email(to: list, subject: str, html: str) -> bool:
    """
    Send HTML email using Resend API

    Args:
        to: List of recipient email addresses
        subject: Email subject line
        html: HTML content of the email

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    # Check for required environment variable
    api_key = os.environ.get('RESEND_API_KEY')
    if not api_key:
        print("Email send error: RESEND_API_KEY environment variable not set")
        return False

    # Configure Resend API client
    resend.api_key = api_key
    try:
        resend.Emails.send({
            "from": "SmartScan Hub <noreply@devnavi.kr>",
            "to": to,
            "subject": subject,
            "html": html,
        })
        return True
    except Exception as e:
        print(f"Email send error: {e}")
        return False