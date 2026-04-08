import json
from html import escape
from common.db import get_client
from common.email_client import send_email

# CORS 응답 헤더
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "https://smartscan-hub.com",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
}


def send_remote_alert(event) -> dict:
    """부모가 가족 구성원에게 원격 알림을 전송하는 핸들러"""

    # OPTIONS 프리플라이트 요청 처리
    if event.get('httpMethod') == 'OPTIONS':
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

    try:
        # Authorization 헤더에서 Bearer 토큰 추출 및 검증
        headers = event.get('headers') or {}
        auth_header = headers.get('Authorization') or headers.get('authorization', '')
        if not auth_header.startswith('Bearer '):
            return {
                "statusCode": 401,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": "인증이 필요합니다."})
            }
        token = auth_header[7:]
        try:
            supabase_auth = get_client()
            user_resp = supabase_auth.auth.get_user(token)
            if not user_resp or not user_resp.user:
                raise ValueError("유효하지 않은 토큰")
        except Exception:
            return {
                "statusCode": 401,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": "인증에 실패했습니다."})
            }

        # 1. API Gateway 이벤트 바디 파싱
        body = json.loads(event.get('body') or '{}')
        member_id = body.get('member_id')
        message = body.get('message', '')

        if not member_id or not message:
            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": "member_id와 message는 필수입니다."})
            }

        supabase = get_client()

        # 2. family_members 테이블에서 이메일 조회
        result = supabase.table('family_members') \
            .select('family_id, user_id, email, name') \
            .eq('id', member_id) \
            .single() \
            .execute()

        member = result.data
        if not member or not member.get('email'):
            return {
                "statusCode": 404,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": "가족 구성원을 찾을 수 없습니다."})
            }

        member_email = member['email']
        member_name = escape(member.get('name', '가족'))
        safe_message = escape(message)

        # 3. 알림 이메일 HTML 구성
        html = f"""
        <div style="font-family:sans-serif;max-width:480px;margin:auto">
          <h2 style="color:#3182ce">📢 SmartScan Hub 원격 알림</h2>
          <p><strong>{member_name}</strong>님에게 보내는 메시지입니다:</p>
          <div style="background:#ebf8ff;padding:16px 24px;border-radius:8px;
                      border-left:4px solid #3182ce;margin:16px 0">
            <p style="margin:0;font-size:15px">{safe_message}</p>
          </div>
          <p style="color:#718096;font-size:13px">SmartScan Hub 자동 발송</p>
        </div>
        """

        # 4. 이메일 발송
        success = send_email([member_email], "📢 원격 알림 - SmartScan Hub", html)

        if not success:
            return {
                "statusCode": 500,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": "이메일 발송에 실패했습니다."})
            }

        # 5. notifications 테이블에 알림 기록 저장 (이메일 성공과 독립 처리)
        try:
            notification_payload = _build_notification_payload(
                sender_user_id=int(user_resp.user.id),
                recipient_member=member,
                message=message
            )
            supabase.table('notifications').insert(notification_payload).execute()
        except Exception as db_err:
            print(f"알림 기록 저장 실패 (이메일은 발송됨): {db_err}")

        print(f"원격 알림 발송 성공: {member_email}")

        # 6. 성공 응답 반환
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({
                "success": True,
                "message": f"{member_name}님에게 알림을 발송했습니다."
            })
        }

    except Exception as e:
        print(f"원격 알림 처리 오류: {e}")
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": "서버 내부 오류가 발생했습니다."})
        }


def _build_notification_payload(sender_user_id: int, recipient_member: dict, message: str) -> dict:
    return {
        "family_id": int(recipient_member["family_id"]),
        "sender_user_id": sender_user_id,
        "recipient_user_id": int(recipient_member["user_id"]),
        "type": "remote",
        "channel": "email",
        "title": "원격 알림",
        "message": message,
        "is_read": False,
    }
