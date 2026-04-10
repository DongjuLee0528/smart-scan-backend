from common.db import get_client


def get_device_by_serial(serial_number: str):
    """시리얼 번호로 디바이스 조회"""
    client = get_client()
    res = (client.table('devices')
           .select('id, family_id')
           .eq('serial_number', serial_number)
           .maybe_single()
           .execute())
    return res.data if res.data else None


def check_missing_items_rpc(device_id: int, scanned_tags: list):
    """RPC 함수 호출하여 누락 물건 확인"""
    client = get_client()
    res = client.rpc('check_missing_items', {
        'p_device_id': device_id,
        'p_tag_uids': scanned_tags
    }).execute()
    return res.data or []
