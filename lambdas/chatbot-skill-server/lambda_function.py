"""
KakaoTalk Chatbot Skill Server Lambda Function

Lambda function that handles integration with KakaoTalk chatbot.
Called through API Gateway POST /chatbot endpoint.

Key Features:
- KakaoTalk chatbot message processing
- Device registration (serial number based)
- Item management (add/delete)
- Device disconnection
- KakaoTalk user registration

Trigger: API Gateway (POST /chatbot)
Users: KakaoTalk chatbot users
"""

import json
import traceback

from common.response import make_res
from services.chatbot_service import handle_chatbot


def lambda_handler(event, context):
    """
    Lambda entry point - Processes KakaoTalk chatbot requests.

    Args:
        event: API Gateway event (KakaoTalk message or web request)
        context: Lambda execution context

    Returns:
        HTTP response (KakaoTalk or web format)
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
            # KakaoTalk chatbot request (with userRequest) or explicit action
            return handle_chatbot(body)

        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "https://smartscan-hub.com"},
            "body": json.dumps({"success": False, "message": "action field is required."}, ensure_ascii=False),
        }

    except Exception:
        print(traceback.format_exc())
        return make_res(False, "A server error occurred.", is_kakao)
