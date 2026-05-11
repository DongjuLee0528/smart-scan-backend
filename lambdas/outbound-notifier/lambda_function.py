"""
Outbound Notification Lambda Function

Lambda function called by inbound-scanner to send email alerts for missing items.
Not directly invoked but called internally by other Lambda functions.

Key Features:
- Email delivery for missing item lists
- Email transmission through Resend API
- Notification record storage in Supabase
- JSON event parsing and error handling

Caller: inbound-scanner Lambda (direct invocation)
"""

import json

from services.notify_service import send_missing_alert


def lambda_handler(event, context):
    """
    Lambda entry point - Sends email alerts for missing items.

    Args:
        event: Event data containing missing item information
        context: Lambda execution context

    Returns:
        HTTP response (statusCode, body)
    """
    # Event type check: May come as JSON string from API Gateway
    if isinstance(event, str):
        try:
            event = json.loads(event)
        except json.JSONDecodeError as e:
            return {
                "statusCode": 400,
                "body": f"Invalid JSON event: {e}",
            }

    if not isinstance(event, dict):
        return {
            "statusCode": 400,
            "body": f"Unsupported event type: {type(event).__name__}",
        }

    try:
        result = send_missing_alert(event)
        return {"statusCode": 200, "body": result}
    except ValueError as e:
        # Configuration errors such as missing environment variables
        print(f"[CONFIG ERROR] {e}")
        return {"statusCode": 500, "body": f"Configuration error: {e}"}
    except Exception as e:
        print(f"[UNHANDLED ERROR] {e}")
        return {"statusCode": 500, "body": f"Internal server error: {e}"}
