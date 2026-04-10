import re

from common.response import make_res, MAIN_QUICK_REPLIES
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

    if not kakao_user_id:
        return make_res(False, "카카오 사용자 ID를 확인할 수 없습니다.", True)

    link = get_user_by_kakao_id(kakao_user_id)
    if not link:
        return make_res(True, (
            "👋 SmartScan Hub에 오신 것을 환영합니다!\n\n"
            "아직 기기가 연결되지 않았습니다.\n\n"
            "📱 기기 연결 방법:\n"
            "1. SmartScan 웹에서 로그인\n"
            "2. [기기 관리] → [카카오 연동]\n"
            "3. 연동 완료 후 이 채팅창으로 돌아오세요\n\n"
            "🌐 https://smartscan-hub.com"
        ), True)

    member_id = link['member_id']

    if '목록' in utterance or '리스트' in utterance:
        return _handle_list(member_id)
    elif '해제' in utterance:
        return _handle_disconnect(kakao_user_id, member_id)
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
        return _handle_add(utterance, member_id)
    elif '삭제' in utterance or '제거' in utterance:
        return _handle_delete(utterance, member_id)
    else:
        return make_res(True, (
            "명령어를 이해하지 못했습니다.\n\n"
            "사용 가능한 명령어:\n"
            "• 물건 목록\n"
            "• [물건명] 추가\n"
            "• [물건명] 삭제\n"
            "• 기기 해제"
        ), True, quick_replies=MAIN_QUICK_REPLIES)


def _handle_list(member_id: int) -> dict:
    items = get_active_items(member_id)
    if not items:
        return make_res(True, "등록된 소지품이 없습니다.\n'[물건명] 추가'로 소지품을 등록해 보세요.", True,
                        quick_replies=MAIN_QUICK_REPLIES)

    lines = [f"{i + 1}. {item['name']}" for i, item in enumerate(items)]
    msg = f"📦 소지품 목록 ({len(items)}개)\n" + "\n".join(lines)
    return make_res(True, msg, True, quick_replies=MAIN_QUICK_REPLIES)


MAX_ITEM_NAME_LEN = 30


def _handle_add(utterance: str, member_id: int) -> dict:
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
    existing = get_active_items(member_id)
    if any(item['name'] == name for item in existing):
        return make_res(False, f"'{name}'은(는) 이미 등록되어 있습니다.", True,
                        quick_replies=MAIN_QUICK_REPLIES)

    add_item(name, member_id)
    return make_res(True, f"✅ '{name}'이(가) 추가되었습니다.\n※ RFID 태그 연결은 웹 사이트에서 진행해 주세요.", True,
                    quick_replies=MAIN_QUICK_REPLIES)


def _handle_delete(utterance: str, member_id: int) -> dict:
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

    count = deactivate_item(name, member_id)
    if count == 0:
        return make_res(False, f"'{name}'을(를) 찾을 수 없습니다.\n'물건 목록'으로 확인해 주세요.", True,
                        quick_replies=MAIN_QUICK_REPLIES)

    return make_res(True, f"🗑️ '{name}'이(가) 삭제되었습니다.", True,
                    quick_replies=MAIN_QUICK_REPLIES)


def _handle_disconnect(kakao_user_id: str, member_id: int) -> dict:
    delete_all_items(member_id)
    delete_user_device(kakao_user_id)
    return make_res(True, "기기 연결이 해제되었습니다.\n소지품 정보도 함께 삭제되었습니다.", True)
