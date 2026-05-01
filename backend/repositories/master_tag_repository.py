"""
Master tag data access layer

Repository responsible for database operations on actual physical RFID tags.
Manages metadata of physical tags attached to devices.

Data management:
- Physical tag information (tag UID, label ID)
- Device-specific tag mapping information
- Label-based tag classification and queries

Business rules:
- Tag UID must be unique throughout entire system
- Master tags belong only to specific devices
- Label ID used for category classification during item registration
- 1:1 matching with items for location tracking

Main use cases:
- Find label-based tags when user registers items
- Tag UID matching during RFID scan data processing
- Manage registered tag lists per device
"""

from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional, List
from backend.models.master_tag import MasterTag


class MasterTagRepository:
    """
    Master tag data access class

    Provides CRUD operations for physical RFID tag information.
    """
    def __init__(self, db: Session):
        """Inject database session"""
        self.db = db

    def get_by_label_id_and_device_id(self, label_id: int, device_id: int) -> Optional[MasterTag]:
        """Find master tag by label ID and device ID (used for item registration)"""
        stmt = select(MasterTag).where(
            MasterTag.label_id == label_id,
            MasterTag.device_id == device_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_tag_uid_and_device_id(self, tag_uid: str, device_id: int) -> Optional[MasterTag]:
        """Find master tag by tag UID and device ID (used for item modification)"""
        stmt = select(MasterTag).where(
            MasterTag.tag_uid == tag_uid,
            MasterTag.device_id == device_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_label_id_by_tag_uid(self, tag_uid: str) -> Optional[int]:
        """Find only label ID by tag UID (for fast matching)"""
        stmt = select(MasterTag.label_id).where(
            MasterTag.tag_uid == tag_uid
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_all_by_device_id(self, device_id: int) -> List[MasterTag]:
        """Find all master tag list of device"""
        stmt = select(MasterTag).where(
            MasterTag.device_id == device_id
        )
        return self.db.execute(stmt).scalars().all()
