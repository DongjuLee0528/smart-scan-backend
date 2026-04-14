"""
아웃바운드 알림 Lambda 함수

inbound-scanner에서 호출되어 누락된 아이템에 대한 이메일 알림을 발송하는 Lambda 함수입니다.
직접 호출되지 않고 다른 Lambda 함수에 의해 내부적으로 호출됩니다.

주요 기능:
- 누락된 아이템 목록을 이메일로 발송
- Resend API를 통한 이메일 전송
- Supabase에 알림 기록 저장
- JSON 이벤트 파싱 및 에러 처리

호출자: inbound-scanner Lambda (직접 호출)
"""

import json

from services.notify_service import send_missing_alert


def lambda_handler(event, context):
    """
    Lambda 진입점 - 누락 아이템 이메일 알림을 발송합니다.

    Args:
        event: 누락된 아이템 정보가 포함된 이벤트 데이터
        context: Lambda 실행 컨텍스트

    Returns:
        HTTP 응답 (statusCode, body)
    """
    # event 타입 체크: API Gateway 등에서 JSON 문자열로 올 수 있음
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
        # 환경변수 미설정 등 설정 오류
        print(f"[CONFIG ERROR] {e}")
        return {"statusCode": 500, "body": f"Configuration error: {e}"}
    except Exception as e:
        print(f"[UNHANDLED ERROR] {e}")
        return {"statusCode": 500, "body": f"Internal server error: {e}"}
