from common.response import make_res
from repositories.tag_repository import get_device_by_serial
from repositories.user_repository import get_user_by_kakao_id, create_user_device, get_first_member_by_family


def register_device(body: dict) -> dict:
    """
    기기 등록 요청 처리
    body: {
      "action": "register_device",
      "userRequest": {"user": {"id": "kakao_user_id"}, "utterance": "..."},
      "params": {"serial_number": "test1234"}   # 또는 body 최상위에 serial_number
    }
    """
    user_req = body.get('userRequest') or {}
    kakao_user_id = user_req.get('user', {}).get('id') or body.get('kakao_user_id')

    params = body.get('params') or body.get('action_params') or {}
    serial_number = params.get('serial_number') or body.get('serial_number', '').strip()

    if not kakao_user_id:
        return make_res(False, "카카오 사용자 ID를 확인할 수 없습니다.", True)
    if not serial_number:
        return make_res(False, "기기 시리얼 번호를 입력해 주세요.", True)

    # 이미 연결된 기기가 있는지 확인
    existing = get_user_by_kakao_id(kakao_user_id)
    if existing:
        return make_res(True, "이미 기기에 연결되어 있습니다.\n다른 기기로 변경하려면 먼저 '기기 해제'를 해주세요.", True)

    # 시리얼 번호로 기기 조회
    device = get_device_by_serial(serial_number)
    if not device:
        return make_res(False, f"시리얼 번호 '{serial_number}'에 해당하는 기기를 찾을 수 없습니다.\n번호를 다시 확인해 주세요.", True)

    # 가족의 대표 구성원 조회
    member = get_first_member_by_family(device['family_id'])
    if not member:
        return make_res(False, "가족 구성원 정보가 없습니다.\n웹 사이트에서 먼저 구성원을 등록해 주세요.", True)

    create_user_device(kakao_user_id, device['id'], member['id'])

    return make_res(True, (
        f"✅ 기기 연결 완료!\n"
        f"기기: {device.get('name') or serial_number}\n"
        f"구성원: {member['name']}\n\n"
        f"사용 가능한 명령어:\n"
        f"• 물건 목록\n"
        f"• [물건명] 추가\n"
        f"• [물건명] 삭제\n"
        f"• 기기 해제"
    ), True)
