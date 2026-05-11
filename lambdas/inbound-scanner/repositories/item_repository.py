"""
Item Repository

Repository functions for device and item-related database operations.
Used by scan service for device lookup and missing item detection.
"""

from common.db import get_client


def get_device_by_serial(serial_number: str):
    """Find device by serial number"""
    client = get_client()
    res = (client.table('devices')
           .select('id, family_id')
           .eq('serial_number', serial_number)
           .maybe_single()
           .execute())
    return res.data if res.data else None


def check_missing_items_rpc(device_id: int, scanned_tags: list):
    """Check for missing items using RPC function

    Calls database RPC function that compares scanned tags against
    registered items for the device to identify missing belongings.

    Args:
        device_id: ID of the scanning device
        scanned_tags: List of RFID tag UIDs that were scanned

    Returns:
        List of missing item details with member information
    """
    client = get_client()
    res = client.rpc('check_missing_items', {
        'p_device_id': device_id,
        'p_tag_uids': scanned_tags
    }).execute()
    return res.data or []
