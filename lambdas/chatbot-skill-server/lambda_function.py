"""
카카오톡 챗봇 스킬 서버 Lambda 함수

카카오톡 챗봇과의 연동을 처리하는 Lambda 함수입니다.
API Gateway POST /chatbot 엔드포인트를 통해 호출됩니다.

주요 기능:
- 카카오톡 챗봇 메시지 처리
- 디바이스 등록 (시리얼 번호 기반)
- 아이템 관리 (추가/삭제)
- 디바이스 연결 해제
- 카카오톡 사용자 등록

트리거: API Gateway (POST /chatbot)
사용자: 카카오톡 챗봇 사용자
"""

import json
import traceback

from common.response import make_res
from services.chatbot_service import handle_chatbot


def lambda_handler(event, context):
    """
    Lambda 진입점 - 카카오톡 챗봇 요청을 처리합니다.

    Args:
        event: API Gateway 이벤트 (카카오톡 메시지 또는 웹 요청)
        context: Lambda 실행 컨텍스트

    Returns:
        HTTP 응답 (카카오톡 또는 웹 형식)
    """
    request_context = event.get('requestContext', {})
    http_info = request_context.get('http', {})
    method = event.get('httpMethod') or http_info.get('method')
    is_web = 'httpMethod' in event or 'http' in request_context

    body = {}
    is_kakao = False
    try:
        if method == 'OPTIONS':
            return make_res(True, "CORS OK")

        raw_body = event.get('body') or '{}'
        body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
        is_kakao = 'userRequest' in body

        if is_kakao or body.get('action') is not None:
            # 카카오 챗봇 요청(userRequest 포함) 또는 명시적 action
            return handle_chatbot(body)

        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "https://smartscan-hub.com"},
            "body": json.dumps({"success": False, "message": "action 필드가 필요합니다."}, ensure_ascii=False),
        }

    except Exception:
        print(traceback.format_exc())
        return make_res(False, "서버 오류가 발생했습니다.", is_kakao)
