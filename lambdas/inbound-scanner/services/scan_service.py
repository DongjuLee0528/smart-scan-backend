import json
import boto3
from datetime import datetime, timezone

from repositories.item_repository import (
    get_device_by_serial,
    check_missing_items_rpc
)

lambda_client = boto3.client('lambda')


def process_scan(event):
    body = json.loads(event.get('body', '{}'))
    serial_number = body.get('device_serial')
    scanned_tags = body.get('tags', [])

    # 디바이스 조회
    device = get_device_by_serial(serial_number)
    if not device:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "등록되지 않은 디바이스입니다."})
        }

    device_id = device['id']

    # 스캔 로그 기록
    _insert_scan_logs(device_id, scanned_tags)

    # RPC로 누락 물건 확인
    missing = check_missing_items_rpc(device_id, scanned_tags)

    if missing:
        # 멤버별로 그룹핑
        grouped = _group_by_member(missing)
        print(f"누락 발생: {grouped}")

        # outbound Lambda 직접 호출
        lambda_client.invoke(
            FunctionName='smartscan-outbound',
            InvocationType='Event',
            Payload=json.dumps({
                'device_id': device_id,
                'missing_by_member': grouped
            })
        )

        missing_names = [item['missing_item'] for item in missing]
        return {
            "statusCode": 200,
            "body": json.dumps({"message": f"누락 물건: {missing_names}"})
        }

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "모든 물건이 확인되었습니다."})
    }


def _insert_scan_logs(device_id: int, scanned_tags: list):
    """스캔 태그별 로그 기록"""
    from common.db import get_client
    client = get_client()

    now = datetime.now(timezone.utc).isoformat()
    rows = [
        {'device_id': device_id, 'tag_uid': tag, 'scanned_at': now}
        for tag in scanned_tags
    ]
    if rows:
        client.table('scan_logs').insert(rows).execute()


def _group_by_member(missing_items: list) -> list:
    """멤버별로 누락 물건 그룹핑"""
    members = {}
    for item in missing_items:
        mid = item['member_id']
        if mid not in members:
            members[mid] = {
                'member_id': mid,
                'member_name': item['member_name'],
                'member_email': item['member_email'],
                'missing_items': []
            }
        members[mid]['missing_items'].append(item['missing_item'])
    return list(members.values())
