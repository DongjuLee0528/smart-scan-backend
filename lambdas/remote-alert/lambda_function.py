"""
Remote Alert Lambda Function

Lambda function used when web users manually send alerts to family members.
Called through API Gateway POST /remote-alert endpoint.

Key Features:
- JWT token-based authentication verification
- Email alert delivery to family members
- Notification record storage in Supabase

Trigger: API Gateway (POST /remote-alert)
"""

from services.remote_service import send_remote_alert


def lambda_handler(event, context):
    """
    Lambda entry point - Processes remote alert requests.

    Args:
        event: API Gateway event (including headers, body)
        context: Lambda execution context

    Returns:
        HTTP response (statusCode, headers, body)
    """
    return send_remote_alert(event)
