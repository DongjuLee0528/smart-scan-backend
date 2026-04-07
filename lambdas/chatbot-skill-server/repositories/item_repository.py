from common.db import get_client


def get_active_items(member_id: int) -> list:
    """member_id의 활성 소지품 목록 조회"""
    res = (get_client()
           .table('items')
           .select('id, name, is_required')
           .eq('member_id', member_id)
           .eq('is_active', True)
           .order('created_at')
           .execute())
    return res.data or []


def add_item(name: str, member_id: int) -> dict:
    """items INSERT → 생성된 row 반환"""
    res = (get_client()
           .table('items')
           .insert({'name': name, 'member_id': member_id, 'is_required': True, 'is_active': True})
           .execute())
    return res.data[0] if res.data else None


def deactivate_item(name: str, member_id: int) -> int:
    """items UPDATE is_active=False → 변경 행 수 반환"""
    res = (get_client()
           .table('items')
           .update({'is_active': False})
           .eq('member_id', member_id)
           .eq('name', name)
           .eq('is_active', True)
           .execute())
    return len(res.data) if res.data else 0


def delete_all_items(member_id: int):
    """member_id의 모든 활성 items 비활성화"""
    get_client().table('items').update({'is_active': False}).eq('member_id', member_id).eq('is_active', True).execute()
