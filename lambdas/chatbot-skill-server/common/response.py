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
