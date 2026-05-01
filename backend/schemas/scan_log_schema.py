"""
Scan log API schemas

Defines API schemas for RFID scan records in Smart Scan system.
Tracks and records found/lost status of items detected by devices.

Main schemas:
- ScanStatus: Scan status (found, lost)
- ScanLogCreateRequest: Scan log creation request
- ScanLogResponse: Scan log detail response

Data structure:
- Scan status: Current detection status of RFID tag
- Item information: Identifier of scanned item
- Time information: Exact time when scan occurred
- Device information: User-device combination that performed scan

Business rules:
- Scan logs are created in real-time
- Consecutive scans with same status can be deduplicated
- Lost status is automatically generated after certain time
- Scan history is core data for item tracking

Usage scenarios:
- Log creation when RFID device detects tag
- Item loss detection and notification triggers
- User belongings movement path tracking
- Family member item usage pattern analysis
"""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict


class ScanStatus(str, Enum):
    """
    Scan status enumeration

    Represents current detection status of RFID tag.
    """
    FOUND = "FOUND"  # Found - tag detected by RFID reader
    LOST = "LOST"  # Lost - tag not detected for certain time


class ScanLogCreateRequest(BaseModel):
    """
    Scan log creation request schema

    Used when RFID device sends tag scan results to server.
    """
    item_id: int  # Scanned item ID
    status: ScanStatus  # Scan status (found/lost)


class ScanLogResponse(BaseModel):
    """
    Scan log detail information response schema

    Delivers all scan log information to client.
    """
    id: int  # Scan log unique ID
    user_device_id: int  # User-device connection ID
    item_id: int  # Scanned item ID
    status: ScanStatus  # Scan status
    scanned_at: datetime  # Scan occurrence time

    model_config = ConfigDict(from_attributes=True)
