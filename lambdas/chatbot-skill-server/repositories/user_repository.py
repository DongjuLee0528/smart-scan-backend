"""
kakao_links 테이블 필요 (Supabase SQL Editor에서 실행):

CREATE TABLE kakao_links (
    kakao_user_id TEXT PRIMARY KEY,
    device_id     BIGINT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    member_id     BIGINT NOT NULL REFERENCES family_members(id) ON DELETE CASCADE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""
from common.db import get_client


def get_user_by_kakao_id(kakao_user_id: str):
    """kakao_user_id로 kakao_links 조회 → {kakao_user_id, device_id, member_id}"""
    res = (get_client()
           .table('kakao_links')
           .select('kakao_user_id, device_id, member_id')
           .eq('kakao_user_id', kakao_user_id)
           .limit(1)
           .execute())
    data = res.data if res else []
    return data[0] if data else None


def create_user_device(kakao_user_id: str, device_id: int, member_id: int):
    """kakao_links INSERT"""
    get_client().table('kakao_links').insert({
        'kakao_user_id': kakao_user_id,
        'device_id': device_id,
        'member_id': member_id,
    }).execute()


def delete_user_device(kakao_user_id: str):
    """kakao_links DELETE"""
    get_client().table('kakao_links').delete().eq('kakao_user_id', kakao_user_id).execute()


def get_first_member_by_family(family_id: int):
    """family_id로 첫 번째 family_member 조회 (owner 우선)"""
    res = (get_client()
           .table('family_members')
           .select('id, name, role')
           .eq('family_id', family_id)
           .order('role', desc=True)    # 'owner' > 'member' 내림차순 → owner 우선
           .limit(1)
           .execute())
    return res.data[0] if res.data else None
