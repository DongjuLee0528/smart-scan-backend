"""
사용자 조회 리포지토리

`users` 테이블 기반 신규 스키마만 사용한다.
(magic link 연동 완료 사용자 = `users.kakao_user_id`에 실제 카카오 UID가 저장된 사용자)

조회 시 `pending_` 접두사는 웹 가입은 했지만 카카오 연동 미완료 상태이므로 None 반환.
"""
import uuid

from common.db import get_client


# ---------------------------------------------------------------------------
# 내부: users 테이블 → family_members → user_devices 조인 조회
# ---------------------------------------------------------------------------

def _get_user_from_users_table(kakao_user_id: str):
    """
    users 테이블에서 kakao_user_id 조회 →
    family_members, user_devices 를 순차 조회하여
    {kakao_user_id, member_id, device_id, user_id} 반환.

    pending_ 으로 시작하는 값은 아직 미연동 상태이므로 None 반환.
    """
    client = get_client()

    user_res = (
        client.table("users")
        .select("id, kakao_user_id")
        .eq("kakao_user_id", kakao_user_id)
        .limit(1)
        .execute()
    )
    if not user_res.data:
        return None

    row = user_res.data[0]
    if row["kakao_user_id"].startswith("pending_"):
        return None

    user_id = row["id"]

    member_res = (
        client.table("family_members")
        .select("id")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not member_res.data:
        return None

    member_id = member_res.data[0]["id"]

    device_res = (
        client.table("user_devices")
        .select("device_id")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    device_id = device_res.data[0]["device_id"] if device_res.data else None

    return {
        "kakao_user_id": kakao_user_id,
        "user_id": user_id,
        "member_id": member_id,
        "device_id": device_id,
    }


# ---------------------------------------------------------------------------
# 공개 인터페이스
# ---------------------------------------------------------------------------

def get_user_by_kakao_id(kakao_user_id: str):
    """
    kakao_user_id 로 사용자 조회 → {kakao_user_id, user_id, device_id, member_id} 또는 None
    """
    return _get_user_from_users_table(kakao_user_id)


def delete_user_device(kakao_user_id: str):
    """
    카카오 연동 해제. users.kakao_user_id 를 `pending_<uuid>` 로 리셋하여
    해당 사용자가 다시 magic link 로 재연동할 수 있도록 한다.
    """
    new_pending = f"pending_{uuid.uuid4().hex}"
    (
        get_client()
        .table("users")
        .update({"kakao_user_id": new_pending})
        .eq("kakao_user_id", kakao_user_id)
        .execute()
    )
