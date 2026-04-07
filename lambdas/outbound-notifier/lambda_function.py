import json

from services.notify_service import send_missing_alert


def lambda_handler(event, context):
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
