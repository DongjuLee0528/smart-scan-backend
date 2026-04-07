from common.db import get_client


def get_device_by_serial(serial_number: str):
    """serial_number로 devices 조회 → {id, family_id, serial_number, name}"""
    res = (get_client()
           .table('devices')
           .select('id, family_id, serial_number, name')
           .eq('serial_number', serial_number)
           .eq('is_active', True)
           .maybe_single()
           .execute())
    return res.data


def get_tag_by_label(device_id: int, label: str):
    """device_id + label로 tag 조회 → {id, tag_uid, item_id, label}"""
    res = (get_client()
           .table('tags')
           .select('id, tag_uid, item_id, label')
           .eq('device_id', device_id)
           .eq('label', label)
           .eq('is_active', True)
           .maybe_single()
           .execute())
    return res.data


def get_available_labels(device_id: int) -> list:
    """device_id에서 태그가 연결된 item 목록에 없는 label 반환 (미사용 슬롯)"""
    res = (get_client()
           .table('tags')
           .select('label, item_id')
           .eq('device_id', device_id)
           .eq('is_active', True)
           .execute())
    tags = res.data or []
    # item_id가 NULL인 태그는 없으므로, 태그가 없는 슬롯은 웹에서 관리
    return [t['label'] for t in tags if t.get('label')]
