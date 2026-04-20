"""
카카오톡 챗봇 비즈니스 로직

카카오톡 i 오픈빌더에서 전송되는 사용자 발화를 처리하는 비즈니스 로직입니다.
자연어 명령을 파싱하여 RFID 태그와 연결된 소지품을 관리합니다.

지원 명령:
- '목록' / '리스트': 등록된 소지품 목록 조회
- '[물건명] 추가': 새로운 소지품 등록
- '[물건명] 삭제': 소지품 비활성화 (스캔 제외)
- '기기 해제': RFID 리더기 등록 해제

비즈니스 규칙:
- 한 디바이스당 하나의 카카오 사용자만 연결 가능
- 기기 해제 시 모든 소지품 삭제
- 임시 전용 사용자 ID 지원 (개발/테스트용)
"""

import os
import re

from common.response import make_res, MAIN_QUICK_REPLIES
from common.token_utils import create_kakao_link_token
from repositories.user_repository import get_user_by_kakao_id, delete_user_device
from repositories.item_repository import get_active_items, add_item, deactivate_item, delete_all_items


def handle_chatbot(body: dict) -> dict:
    """
    카카오 챗봇 발화 처리
    utterance 키워드 기반 분기:
      - '목록' / '리스트'  → 소지품 목록
      - '[물건명] 추가'    → 소지품 추가
      - '[물건명] 삭제'    → 소지품 비활성화
      - '기기 해제'        → 기기 연결 해제
    """
    user_req = body.get('userRequest') or {}
    kakao_user_id = user_req.get('user', {}).get('id') or body.get('kakao_user_id', '')
    utterance = (user_req.get('utterance') or body.get('utterance') or '').strip()

    print(f"[DEBUG] kakao_user_id={kakao_user_id}")
    if not kakao_user_id:
        return make_res(False, "카카오 사용자 ID를 확인할 수 없습니다.", True)

    link = get_user_by_kakao_id(kakao_user_id)
    if not link:
        # 웹 계정과 연동되지 않은 사용자 → magic link 발급 후 버튼으로 전달
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

    # A-full: member_id 기반 DB 직접 접근 대신 kakao_user_id 기반 HTTP API 호출로 통일.
    # member_id는 (호환성 목적으로) link dict에 남아 있지만 이제는 사용하지 않는다.
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
    # "지갑 추가", "지갑추가", "추가 지갑" 등 처리
    # 이모지/접두사 제거 후 처리: "➕ 물품 추가" → "물품 추가"
    clean = re.sub(r'^[^\w가-힣]+', '', utterance).strip()
    m = re.search(r'(.+?)\s*추가|추가\s*(.+)', clean)
    if not m:
        return make_res(False, "형식: [물건명] 추가\n예) 지갑 추가", True,
                        quick_replies=MAIN_QUICK_REPLIES)

    name = (m.group(1) or m.group(2) or '').strip()
    # "물품 추가" 버튼 그대로 눌렀을 때 name="물품"이 되는 경우 안내
    if not name or name == '물품':
        return make_res(False, "물건 이름을 입력해 주세요.\n예) 지갑 추가", True,
                        quick_replies=MAIN_QUICK_REPLIES)

    if len(name) > MAX_ITEM_NAME_LEN:
        return make_res(False, f"물건 이름은 {MAX_ITEM_NAME_LEN}자 이하로 입력해 주세요.", True,
                        quick_replies=MAIN_QUICK_REPLIES)

    # 중복 확인
    existing = get_active_items(kakao_user_id)
    if any(item.get('name') == name for item in existing):
        return make_res(False, f"'{name}'은(는) 이미 등록되어 있습니다.", True,
                        quick_replies=MAIN_QUICK_REPLIES)

    add_item(name, kakao_user_id)
    return make_res(True, f"✅ '{name}'이(가) 추가되었습니다.\n※ RFID 태그 연결은 웹 사이트에서 진행해 주세요.", True,
                    quick_replies=MAIN_QUICK_REPLIES)


def _handle_delete(utterance: str, kakao_user_id: str) -> dict:
    # "지갑 삭제", "지갑 제거"
    # 이모지/접두사 제거 후 처리: "❌ 물품 삭제" → "물품 삭제"
    clean = re.sub(r'^[^\w가-힣]+', '', utterance).strip()
    m = re.search(r'(.+?)\s*(삭제|제거)', clean)
    if not m:
        return make_res(False, "형식: [물건명] 삭제\n예) 지갑 삭제", True,
                        quick_replies=MAIN_QUICK_REPLIES)

    name = m.group(1).strip()
    # "물품 삭제" 버튼 그대로 눌렀을 때 name="물품"이 되는 경우 안내
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
    # 먼저 아이템 일괄 soft-delete (HTTP 백엔드). 그 후 users.kakao_user_id 를 pending_으로 리셋.
    delete_all_items(kakao_user_id)
    delete_user_device(kakao_user_id)
    return make_res(True, "기기 연결이 해제되었습니다.\n소지품 정보도 함께 삭제되었습니다.", True)
