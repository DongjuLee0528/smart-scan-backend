"""
원격 알림 이메일 발송 클라이언트

Smart Scan 시스템의 원격 알림 Lambda에서 긴급 상황이나 중요 이벤트 발생 시
즉시 이메일 알림을 발송하는 클라이언트입니다. Resend 서비스를 통해 안정적이고 빠른 이메일 전송을 제공합니다.

주요 기능:
- Resend API를 통한 고속 이메일 발송
- 환경변수 기반 API 키 관리
- 한국어 에러 메시지를 통한 개발자 친화적 오류 처리
- 브랜딩된 발송자 정보 (SmartScan Hub)

사용 컨텍스트:
- 긴급 상황 감지 시 즉시 알림 발송
- 보안 이벤트 또는 침입 감지 알림
- 시스템 장애나 중요한 상태 변화 통지
- 원격 모니터링 및 관리 알림

이메일 발송 시나리오:
- 침입자 감지나 보안 위협 상황
- 시스템 임계값 초과나 장애 발생
- 사용자 정의 규칙에 따른 특별한 이벤트 발생
- 원격 관리가 필요한 상황 발생

기술적 특징:
- Lambda Cold Start 최적화를 위한 모듈 레벨 초기화
- 예외 처리를 통한 안정적인 알림 발송 보장
- HTML 형식 이메일 지원으로 풍부한 알림 내용 제공
"""

import os
import resend

# Resend API 키 초기화 (Lambda Cold Start 최적화)
_api_key = os.environ.get('RESEND_API_KEY')
if not _api_key:
    raise ValueError("환경변수 RESEND_API_KEY가 설정되지 않았습니다.")
resend.api_key = _api_key


def send_email(to: list, subject: str, html: str) -> bool:
    """
    원격 알림 이메일 발송

    긴급 상황이나 중요 이벤트 발생 시 지정된 수신자들에게
    즉시 이메일 알림을 발송합니다.

    Args:
        to: 수신자 이메일 주소 목록
        subject: 이메일 제목
        html: HTML 형식의 이메일 내용

    Returns:
        bool: 발송 성공 여부

    예외 처리:
        - Resend API 오류 시 False 반환 및 오류 로깅
        - 네트워크 오류나 인증 실패 시에도 안정적 처리

    발송자 정보:
        - 발송자: "SmartScan Hub <noreply@smartscan-hub.com>"
        - 브랜딩된 발송자로 신뢰성 있는 알림 제공
    """
    try:
        resend.Emails.send({
            "from": "SmartScan Hub <noreply@smartscan-hub.com>",  # 브랜딩된 발송자 정보
            "to": to,  # 수신자 목록
            "subject": subject,  # 알림 제목
            "html": html,  # HTML 형식 알림 내용
        })
        return True
    except Exception as e:
        print(f"이메일 발송 오류: {e}")
        return False
