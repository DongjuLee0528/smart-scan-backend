import json
import logging
import boto3
from datetime import datetime, timezone

from common.db import get_client
from repositories.item_repository import (
    get_device_by_serial,
    check_missing_items_rpc
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

lambda_client = boto3.client('lambda', region_name='ap-northeast-2')


def process_scan(event):
    try:
        raw_body = event.get('body', '{}')
        body = json.loads(raw_body) if isinstance(raw_body, str) else raw_body
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning("요청 body 파싱 실패: %s", str(e))
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "요청 형식이 올바르지 않습니다."})
        }

    serial_number = body.get('device_serial')
    scanned_tags = body.get('tags', [])

    if not serial_number or not isinstance(serial_number, str):
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "device_serial 값이 필요합니다."})
        }

    if not isinstance(scanned_tags, list):
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "tags는 배열이어야 합니다."})
        }

    # 디바이스 조회
    device = get_device_by_serial(serial_number)
    if not device:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "등록되지 않은 디바이스입니다."})
        }

    device_id = device['id']

    # 스캔 로그 기록 (실패해도 스캔 결과 반환에 영향 없음)
    _insert_scan_logs(device_id, scanned_tags)

    # RPC로 누락 물건 확인
    missing = check_missing_items_rpc(device_id, scanned_tags)

    if missing:
        # 멤버별로 그룹핑
        grouped = _group_by_member(missing)
        missing_names = [item['missing_item'] for item in missing]
        logger.info(
            "누락 발생 — device_id: %s, 누락 물건 수: %d, 멤버 수: %d",
            device_id, len(missing_names), len(grouped)
        )

        # outbound Lambda 직접 호출 (실패해도 스캔 결과 정상 반환)
        try:
            lambda_client.invoke(
                FunctionName='smartscan-outbound',
                InvocationType='Event',
                Payload=json.dumps({
                    'device_id': device_id,
                    'missing_by_member': grouped
                })
            )
        except Exception as e:
            logger.error("outbound Lambda 호출 실패 — device_id: %s, error: %s", device_id, str(e))

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
    if not scanned_tags:
        return

    try:
        client = get_client()
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            {'device_id': device_id, 'tag_uid': tag, 'scanned_at': now}
            for tag in scanned_tags
        ]
        client.table('scan_logs').insert(rows).execute()
    except Exception as e:
        logger.error("scan_logs insert 실패 — device_id: %s, error: %s", device_id, str(e))


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
