"""
인바운드 스캔 처리 Lambda 함수

라즈베리파이 RFID 리더기에서 스캔 데이터를 받아 처리하는 Lambda 함수입니다.
API Gateway POST /inbound 엔드포인트를 통해 호출됩니다.

주요 기능:
- RFID 스캔 데이터 검증 및 처리
- 누락된 아이템 감지
- 자동으로 outbound-notifier Lambda 호출하여 이메일 알림 발송
- Supabase에 스캔 로그 저장

트리거: API Gateway (POST /inbound)
데이터 소스: 라즈베리파이 UHF RFID 리더기
"""

from services.scan_service import process_scan


def lambda_handler(event, context):
    """
    Lambda 진입점 - RFID 스캔 데이터를 처리합니다.

    Args:
        event: API Gateway 이벤트 (RFID 스캔 데이터 포함)
        context: Lambda 실행 컨텍스트

    Returns:
        HTTP 응답 (statusCode, headers, body)
    """
    return process_scan(event)
