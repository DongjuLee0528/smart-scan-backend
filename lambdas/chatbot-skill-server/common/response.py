"""
카카오톡 챗봇 응답 생성 유틸리티

SmartScan 카카오톡 챗봇의 응답 메시지를 생성하는 공통 유틸리티 함수들을 제공합니다.
카카오톡 챗봇 API 스펙에 맞는 응답 형식과 일반 HTTP API 응답을 모두 지원합니다.

주요 기능:
- 카카오톡 챗봇 응답 형식 변환 (basicCard, simpleText)
- 퀵리플라이 버튼 및 액션 버튼 지원
- CORS 헤더 및 보안 설정 관리
- SmartScan 브랜딩 이미지 및 메뉴 구성

응답 형식:
- 일반 API: JSON 형태의 success/message 구조
- 카카오톡 봇: kakao i 스킬 응답 스펙 (v2.0) 준수

비즈니스 컨텍스트:
- 소지품 관리 명령어에 대한 사용자 친화적 인터페이스 제공
- 메인 메뉴를 통한 핵심 기능 빠른 접근
- 시각적 카드 형태로 정보 전달 및 액션 유도
"""

import json

ALLOWED_ORIGIN = "https://smartscan-hub.com"
CARD_IMG_URL = "https://cdn-icons-png.flaticon.com/512/553/553376.png"

_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Headers": "Content-Type, X-Requested-With",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
}

# 메인 메뉴 퀵리플라이 버튼
MAIN_QUICK_REPLIES = [
    {"label": "📋 목록 확인",  "action": "message", "messageText": "목록"},
    {"label": "➕ 물품 추가",  "action": "message", "messageText": "추가"},
    {"label": "❌ 물품 삭제",  "action": "message", "messageText": "삭제"},
    {"label": "❌ 기기 해제",  "action": "message", "messageText": "기기 해제"},
]


def make_res(success: bool, message: str, is_kakao: bool = False, buttons=None, quick_replies=None) -> dict:
    """
    카카오톡 챗봇 또는 일반 API 응답 생성

    요청 타입에 따라 적절한 응답 형식을 생성합니다.
    카카오톡 챗봇의 경우 스킬 응답 스펙에 맞게 변환하고,
    일반 API의 경우 간단한 JSON 형식으로 응답합니다.

    Args:
        success: 응답 성공 여부
        message: 사용자에게 표시할 메시지
        is_kakao: 카카오톡 챗봇 응답 여부
        buttons: 카카오톡 카드에 포함할 액션 버튼 목록 (선택사항)
        quick_replies: 빠른 응답 버튼 목록 (선택사항)

    Returns:
        dict: Lambda 응답 형식 (statusCode, headers, body 포함)

    응답 형태:
        - is_kakao=False: {"success": bool, "message": str}
        - is_kakao=True: kakao i 스킬 응답 스펙 (basicCard 또는 simpleText)

    사용 예시:
        물품 목록 조회 성공 시 메인 메뉴 퀵리플라이와 함께 응답
    """
    if not is_kakao:
        return {
            "statusCode": 200,
            "headers": _HEADERS,
            "body": json.dumps({"success": success, "message": str(message)}, ensure_ascii=False),
        }

    output = (
        {"basicCard": {"title": "SmartScan Hub", "description": str(message),
                       "thumbnail": {"imageUrl": CARD_IMG_URL}, "buttons": buttons}}
        if buttons else {"simpleText": {"text": str(message)}}
    )

    template: dict = {"outputs": [output]}
    if quick_replies:
        template["quickReplies"] = quick_replies

    return {
        "statusCode": 200,
        "headers": _HEADERS,
        "body": json.dumps({"version": "2.0", "template": template}, ensure_ascii=False),
    }
