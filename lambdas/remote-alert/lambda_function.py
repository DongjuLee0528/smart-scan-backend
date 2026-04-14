"""
원격 알림 Lambda 함수

웹 사용자가 가족 구성원에게 수동으로 알림을 보낼 때 사용되는 Lambda 함수입니다.
API Gateway POST /remote-alert 엔드포인트를 통해 호출됩니다.

주요 기능:
- JWT 토큰 기반 인증 검증
- 가족 구성원에게 이메일 알림 발송
- Supabase에 알림 기록 저장

트리거: API Gateway (POST /remote-alert)
"""

from services.remote_service import send_remote_alert


def lambda_handler(event, context):
    """
    Lambda 진입점 - 원격 알림 요청을 처리합니다.

    Args:
        event: API Gateway 이벤트 (headers, body 포함)
        context: Lambda 실행 컨텍스트

    Returns:
        HTTP 응답 (statusCode, headers, body)
    """
    return send_remote_alert(event)
