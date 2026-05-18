"""
KakaoTalk Chatbot Response Generation Utility

Provides common utility functions for generating SmartScan KakaoTalk chatbot response messages.
Supports both response formats compliant with KakaoTalk chatbot API specs and general HTTP API responses.

Key Features:
- KakaoTalk chatbot response format conversion (basicCard, simpleText)
- Quick reply buttons and action button support
- CORS headers and security configuration management
- SmartScan branding images and menu configuration

Response Formats:
- General API: JSON structure with success/message format
- KakaoTalk Bot: Complies with kakao i skill response spec (v2.0)

Business Context:
- Provides user-friendly interface for item management commands
- Quick access to core features through main menu
- Information delivery and action guidance in visual card format
"""

import json

ALLOWED_ORIGIN = "https://smartscan-hub.com"
CARD_IMG_URL = "https://cdn-icons-png.flaticon.com/512/553/553376.png"

_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Headers": "Content-Type, X-Requested-With",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
}

# Main menu quick reply buttons
MAIN_QUICK_REPLIES = [
    {"label": "목록 확인",  "action": "message", "messageText": "목록"},
    {"label": "물품 추가",  "action": "message", "messageText": "추가"},
    {"label": "물품 삭제",  "action": "message", "messageText": "삭제"},
    {"label": "기기 해제",  "action": "message", "messageText": "기기 해제"},
]


def make_res(success: bool, message: str, is_kakao: bool = False, buttons=None, quick_replies=None) -> dict:
    """
    Generate KakaoTalk chatbot or general API response

    Generates appropriate response format based on request type.
    For KakaoTalk chatbot, converts to skill response spec format,
    for general API, responds in simple JSON format.

    Args:
        success: Response success status
        message: Message to display to user
        is_kakao: Whether this is a KakaoTalk chatbot response
        buttons: List of action buttons to include in KakaoTalk card (optional)
        quick_replies: List of quick reply buttons (optional)

    Returns:
        dict: Lambda response format (includes statusCode, headers, body)

    Response formats:
        - is_kakao=False: {"success": bool, "message": str}
        - is_kakao=True: kakao i skill response spec (basicCard or simpleText)

    Usage example:
        Item list query success with main menu quick replies response
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
