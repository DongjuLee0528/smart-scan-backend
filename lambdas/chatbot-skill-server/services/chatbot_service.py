"""
KakaoTalk Chatbot Business Logic

Business logic to process user utterances sent from KakaoTalk i OpenBuilder.
Parses natural language commands to manage belongings connected to RFID tags.

Supported Commands:
- 'list' / 'list': View registered belongings list
- '[item name] add': Register new belongings
- '[item name] delete': Deactivate belongings (exclude from scanning)
- 'device disconnect': Unregister RFID reader device

Business Rules:
- Only one Kakao user can be connected per device
- All belongings are deleted when device is disconnected
- Temporary dedicated user ID support (for development/testing)
"""

import os
import re

from common.response import make_res, MAIN_QUICK_REPLIES
from common.token_utils import create_kakao_link_token
from repositories.user_repository import get_user_by_kakao_id, delete_user_device
from repositories.item_repository import get_active_items, add_item, deactivate_item, delete_all_items


def handle_chatbot(body: dict) -> dict:
    """
    Handle Kakao chatbot utterances
    Branch based on utterance keywords:
      - 'list' / 'list'      → belongings list
      - '[item name] add'     → add belongings
      - '[item name] delete'  → deactivate belongings
      - 'device disconnect'   → disconnect device
    """
    user_req = body.get('userRequest') or {}
    kakao_user_id = user_req.get('user', {}).get('id') or body.get('kakao_user_id', '')
    utterance = (user_req.get('utterance') or body.get('utterance') or '').strip()

    print(f"[DEBUG] kakao_user_id={kakao_user_id}")
    if not kakao_user_id:
        return make_res(False, "카카오 사용자 ID를 확인할 수 없습니다.", True)

    link = get_user_by_kakao_id(kakao_user_id)
    if not link:
        # User not linked with web account → issue magic link and deliver via button
        token = create_kakao_link_token(kakao_user_id)
        web_base_url = os.environ.get("SMARTSCAN_WEB_URL", "https://smartscan-hub.com").rstrip("/")
        link_url = f"{web_base_url}/link-kakao.html?token={token}"
        return make_res(True, (
            "👋 SmartScan Hub에 오신 것을 환영합니다!\n\n"
            "웹 계정과 카카오톡 연동이 필요합니다.\n"
            "아래 버튼을 눌러 SmartScan에 로그인한 뒤\n"
            "연동을 완료해 주세요.\n\n"
            "⏱ 링크는 5분간 유효합니다."
        ), True, buttons=[
            {"label": "🔗 계정 연동하기", "action": "webLink", "webLinkUrl": link_url}
        ])

    # A-full: Unified to kakao_user_id-based HTTP API calls instead of member_id-based direct DB access.
    # member_id remains in link dict (for compatibility purposes) but is no longer used.
    _ = link.get('member_id')

    if '목록' in utterance or '리스트' in utterance:
        return _handle_list(kakao_user_id)
    elif '해제' in utterance:
        return _handle_disconnect(kakao_user_id)
    elif '등록' in utterance:
        return make_res(True, (
            "기기 등록 방법:\n\n"
            "1. SmartScan 웹에서 로그인\n"
            "2. [기기 관리] → [기기 등록]\n"
            "3. 기기 시리얼 번호 입력 후 등록\n\n"
            "기기 등록은 웹에서만 가능합니다.\n\n"
            "🌐 https://smartscan-hub.com"
        ), True, quick_replies=MAIN_QUICK_REPLIES)
    elif '추가' in utterance:
        return _handle_add(utterance, kakao_user_id)
    elif '삭제' in utterance or '제거' in utterance:
        return _handle_delete(utterance, kakao_user_id)
    else:
        return make_res(True, (
            "명령어를 이해하지 못했습니다.\n\n"
            "사용 가능한 명령어:\n"
            "• 물건 목록\n"
            "• [물건명] 추가\n"
            "• [물건명] 삭제\n"
            "• 기기 해제"
        ), True, quick_replies=MAIN_QUICK_REPLIES)


def _handle_list(kakao_user_id: str) -> dict:
    items = get_active_items(kakao_user_id)
    if not items:
        return make_res(True, "등록된 소지품이 없습니다.\n'[물건명] 추가'로 소지품을 등록해 보세요.", True,
                        quick_replies=MAIN_QUICK_REPLIES)

    lines = [f"{i + 1}. {item['name']}" for i, item in enumerate(items)]
    msg = f"📦 소지품 목록 ({len(items)}개)\n" + "\n".join(lines)
    return make_res(True, msg, True, quick_replies=MAIN_QUICK_REPLIES)


MAX_ITEM_NAME_LEN = 30


def _handle_add(utterance: str, kakao_user_id: str) -> dict:
    # Handle "wallet add", "walletadd", "add wallet" etc.
    # Process after removing emoji/prefix: "➕ item add" → "item add"
    clean = re.sub(r'^[^\w가-힣]+', '', utterance).strip()
    m = re.search(r'(.+?)\s*추가|추가\s*(.+)', clean)
    if not m:
        return make_res(False, "형식: [물건명] 추가\n예) 지갑 추가", True,
                        quick_replies=MAIN_QUICK_REPLIES)

    name = (m.group(1) or m.group(2) or '').strip()
    # Guide when pressing "item add" button as-is results in name="item"
    if not name or name == '물품':
        return make_res(False, "물건 이름을 입력해 주세요.\n예) 지갑 추가", True,
                        quick_replies=MAIN_QUICK_REPLIES)

    if len(name) > MAX_ITEM_NAME_LEN:
        return make_res(False, f"물건 이름은 {MAX_ITEM_NAME_LEN}자 이하로 입력해 주세요.", True,
                        quick_replies=MAIN_QUICK_REPLIES)

    # Check for duplicates
    existing = get_active_items(kakao_user_id)
    if any(item.get('name') == name for item in existing):
        return make_res(False, f"'{name}'은(는) 이미 등록되어 있습니다.", True,
                        quick_replies=MAIN_QUICK_REPLIES)

    add_item(name, kakao_user_id)
    return make_res(True, f"✅ '{name}'이(가) 추가되었습니다.\n※ RFID 태그 연결은 웹 사이트에서 진행해 주세요.", True,
                    quick_replies=MAIN_QUICK_REPLIES)


def _handle_delete(utterance: str, kakao_user_id: str) -> dict:
    # "wallet delete", "wallet remove"
    # Process after removing emoji/prefix: "❌ item delete" → "item delete"
    clean = re.sub(r'^[^\w가-힣]+', '', utterance).strip()
    m = re.search(r'(.+?)\s*(삭제|제거)', clean)
    if not m:
        return make_res(False, "형식: [물건명] 삭제\n예) 지갑 삭제", True,
                        quick_replies=MAIN_QUICK_REPLIES)

    name = m.group(1).strip()
    # Guide when pressing "item delete" button as-is results in name="item"
    if not name or name == '물품':
        return make_res(False, "물건 이름을 입력해 주세요.\n예) 지갑 삭제", True,
                        quick_replies=MAIN_QUICK_REPLIES)

    count = deactivate_item(name, kakao_user_id)
    if count == 0:
        return make_res(False, f"'{name}'을(를) 찾을 수 없습니다.\n'물건 목록'으로 확인해 주세요.", True,
                        quick_replies=MAIN_QUICK_REPLIES)

    return make_res(True, f"🗑️ '{name}'이(가) 삭제되었습니다.", True,
                    quick_replies=MAIN_QUICK_REPLIES)


def _handle_disconnect(kakao_user_id: str) -> dict:
    # First bulk soft-delete items (HTTP backend). Then reset users.kakao_user_id to pending_.
    delete_all_items(kakao_user_id)
    delete_user_device(kakao_user_id)
    return make_res(True, "기기 연결이 해제되었습니다.\n소지품 정보도 함께 삭제되었습니다.", True)
