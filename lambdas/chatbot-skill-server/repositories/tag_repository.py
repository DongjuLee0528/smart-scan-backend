"""
Tag and device data repository for KakaoTalk chatbot

Database access layer for querying RFID tag and device information from the KakaoTalk chatbot.
Provides functionality to manage physical RFID tag connection status and available label slots.

Key Features:
- Query device by serial number (for device authentication)
- Query tags by label and device combination
- Check available label slots on device

Business Context:
- Check device connection status from KakaoTalk chatbot
- Validate available labels when adding new items
- Manage physical connection between RFID tags and items

Data Structure:
- devices: Physical RFID reader information
- tags: Physical RFID tags connected to devices
- label: Physical location identifier for tags (slots 1~N)

Usage Scenarios:
- Label verification when user adds items via KakaoTalk
- Device registration and connection status validation
- Query availability of physical tag slots
"""

from common.db import get_client


def get_device_by_serial(serial_number: str):
    """
    Query device by serial number

    Function used for KakaoTalk chatbot authentication, queries registered
    device information using the device serial number provided by the user.

    Args:
        serial_number: Unique serial number of the RFID reader

    Returns:
        dict | None: Device information or None
                     Contains {id, family_id, serial_number, name}

    Business Logic:
        - Only queries devices with active status (is_active=True)
        - Prepares user permission validation by family ID
        - For device authentication and connection status verification

    Usage Example:
        Device ownership verification during KakaoTalk chatbot login
    """
    res = (get_client()
           .table('devices')
           .select('id, family_id, serial_number, name')
           .eq('serial_number', serial_number)
           .eq('is_active', True)
           .maybe_single()
           .execute())
    return res.data


def get_tag_by_label(device_id: int, label: str):
    """
    Query tag by device ID and label

    Queries physical RFID tag information connected to a specified label slot of a specific device.
    Used to check tag availability for the label when adding/modifying items.

    Args:
        device_id: RFID reader device ID
        label: Physical tag slot number (1, 2, 3, ... N)

    Returns:
        dict | None: Tag information or None
                     Contains {id, tag_uid, item_id, label}

    Data Structure:
        - tag_uid: Unique identifier of physical RFID tag
        - item_id: Connected item ID (NULL if unused slot)
        - label: Physical slot location identifier

    Usage Example:
        Check availability of label 3 when user commands "add wallet 3"
    """
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
    """
    Query available label slot list on device

    Returns the label list of all currently registered tags on the specified device.
    Used to guide available labels when adding items via KakaoTalk chatbot.

    Args:
        device_id: RFID reader device ID

    Returns:
        list: Label list of registered tags (string format)

    Business Logic:
        - Only queries tags with active status
        - Assumes no tags with NULL item_id exist
        - Unused slot management performed on web

    Usage Example:
        Guide available labels when user commands "add"
        "Currently items are registered on labels 1, 2, 3"
    """
    res = (get_client()
           .table('tags')
           .select('label, item_id')
           .eq('device_id', device_id)
           .eq('is_active', True)
           .execute())
    tags = res.data or []
    # No tags with NULL item_id, so slots without tags are managed on the web
    return [t['label'] for t in tags if t.get('label')]
