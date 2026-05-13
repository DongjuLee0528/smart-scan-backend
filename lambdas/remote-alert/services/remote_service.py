import json
from html import escape
from common.db import get_client
from common.email_client import send_email

# CORS response headers
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "https://smartscan-hub.com",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
}


def send_remote_alert(event) -> dict:
    """Handler for parents to send remote alerts to family members"""

    # Handle OPTIONS preflight requests
    if event.get('httpMethod') == 'OPTIONS':
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

    try:
        # Extract and validate Bearer token from Authorization header
        headers = event.get('headers') or {}
        auth_header = headers.get('Authorization') or headers.get('authorization', '')
        if not auth_header.startswith('Bearer '):
            return {
                "statusCode": 401,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": "Authentication required."})
            }
        token = auth_header[7:]
        try:
            supabase_auth = get_client()
            user_resp = supabase_auth.auth.get_user(token)
            if not user_resp or not user_resp.user:
                raise ValueError("Invalid token")
        except Exception:
            return {
                "statusCode": 401,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": "Authentication failed."})
            }

        # 1. Parse API Gateway event body
        body = json.loads(event.get('body') or '{}')
        member_id = body.get('member_id')
        message = body.get('message', '')

        if not member_id or not message:
            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": "member_id and message are required."})
            }

        MAX_MESSAGE_LEN = 500
        if len(str(message)) > MAX_MESSAGE_LEN:
            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": f"Message must be {MAX_MESSAGE_LEN} characters or less."})
            }

        supabase = get_client()

        # 2. Query email from family_members table
        result = supabase.table('family_members') \
            .select('family_id, email, name') \
            .eq('id', member_id) \
            .single() \
            .execute()

        member = result.data
        if not member or not member.get('email'):
            return {
                "statusCode": 404,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": "Family member not found."})
            }

        member_email = member['email']
        member_name = escape(member.get('name', 'Family Member'))
        safe_message = escape(message)

        # 3. Compose alert email HTML
        html = f"""
        <div style="font-family:sans-serif;max-width:480px;margin:auto">
          <h2 style="color:#3182ce">📢 SmartScan Hub Remote Alert</h2>
          <p>Message for <strong>{member_name}</strong>:</p>
          <div style="background:#ebf8ff;padding:16px 24px;border-radius:8px;
                      border-left:4px solid #3182ce;margin:16px 0">
            <p style="margin:0;font-size:15px">{safe_message}</p>
          </div>
          <p style="color:#718096;font-size:13px">Sent automatically by SmartScan Hub</p>
        </div>
        """

        # 4. Send email
        success = send_email([member_email], "📢 Remote Alert - SmartScan Hub", html)

        if not success:
            return {
                "statusCode": 500,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": "Failed to send email."})
            }

        # 5. Save notification record to notifications table (independent from email success)
        try:
            supabase.table('notifications').insert({
                "member_id": member_id,
                "type": "remote",
                "title": "Remote Alert",
                "message": escape(str(message)),
                "sent_via": "email",
            }).execute()
        except Exception as db_err:
            print(f"Failed to save notification record (email was sent): {db_err}")

        print(f"Remote alert sent successfully: {member_email}")

        # 6. Return success response
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({
                "success": True,
                "message": f"Alert sent to {member_name}."
            })
        }

    except Exception as e:
        print(f"Remote alert processing error: {e}")
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": "Internal server error occurred."})
        }


def _build_notification_payload(sender_user_id: int, recipient_member: dict, message: str) -> dict:
    return {
        "family_id": int(recipient_member["family_id"]),
        "sender_user_id": sender_user_id,
        "recipient_user_id": int(recipient_member["user_id"]),
        "type": "remote",
        "channel": "email",
        "title": "Remote Alert",
        "message": message,
        "is_read": False,
    }
