"""
User-device data access layer

Repository managing connection information between users and devices in Smart Scan system.
Manages user access permissions for family-shared devices.

Data management:
- Create and delete user-device connections
- Query device registration status and connection info
- Validate user device access permissions

Business rules:
- One device shared per family
- All family members automatically connected to same device
- Device connection distributed to all family members upon registration
- All connections deleted simultaneously when device is unlinked

Main use cases:
- Create user connections when registering family device
- Validate user device access permissions
- Use in item management and scan data processing
"""

from typing import Optional

from sqlalchemy.orm import Session, joinedload

from backend.models.user import User
from backend.models.user_device import UserDevice


class UserDeviceRepository:
    """
    User-device connection data access class

    Provides CRUD operations for managing connection state between users and devices.
    """
    def __init__(self, db: Session):
        """Inject database session"""
        self.db = db

    def find_by_user_and_device(self, user_id: int, device_id: int) -> Optional[UserDevice]:
        """Find connection info by user ID and device ID"""
        return self.db.query(UserDevice).options(
            joinedload(UserDevice.device)
        ).filter(
            UserDevice.user_id == user_id,
            UserDevice.device_id == device_id
        ).first()

    def find_by_user_id(self, user_id: int) -> Optional[UserDevice]:
        """Find device connection info by user ID"""
        return self.db.query(UserDevice).options(
            joinedload(UserDevice.device)
        ).filter(UserDevice.user_id == user_id).first()

    def get_by_kakao_user_id(self, kakao_user_id: str) -> Optional[UserDevice]:
        """Find device connection info by KakaoTalk user ID (used in lambda)"""
        return self.db.query(UserDevice).join(User).options(
            joinedload(UserDevice.device)
        ).filter(User.kakao_user_id == kakao_user_id).first()

    def find_all_by_device_id(self, device_id: int) -> list[UserDevice]:
        """Find all users connected to device"""
        return self.db.query(UserDevice).options(
            joinedload(UserDevice.device)
        ).filter(UserDevice.device_id == device_id).all()

    def find_all_by_user_ids(self, user_ids: list[int]) -> list[UserDevice]:
        """Find device connection info for multiple users"""
        if not user_ids:
            return []

        return self.db.query(UserDevice).options(
            joinedload(UserDevice.device)
        ).filter(UserDevice.user_id.in_(user_ids)).all()

    def create(self, user_id: int, device_id: int) -> UserDevice:
        """Create new user-device connection"""
        user_device = UserDevice(user_id=user_id, device_id=device_id)
        self.db.add(user_device)
        self.db.flush()
        return user_device

    def delete(self, user_device: UserDevice) -> None:
        """Delete user-device connection"""
        self.db.delete(user_device)
        self.db.flush()

    def delete_many(self, user_devices: list[UserDevice]) -> None:
        """Batch delete multiple user-device connections"""
        for user_device in user_devices:
            self.db.delete(user_device)
        self.db.flush()