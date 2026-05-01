from sqlalchemy.orm import Session

from backend.common.exceptions import ForbiddenException, NotFoundException
from backend.common.validator import validate_positive_int
from backend.repositories.family_member_repository import FamilyMemberRepository
from backend.repositories.item_repository import ItemRepository
from backend.repositories.scan_log_repository import ScanLogRepository
from backend.repositories.user_device_repository import UserDeviceRepository
from backend.schemas.scan_log_schema import ScanLogResponse, ScanStatus


class ScanLogService:
    """
    Scan log management service

    Handles recording and retrieval of scan events from user devices.
    Processes FOUND/LOST status scan logs to provide tag location tracking data.

    Design principles:
    - Location tracking logs: Store all scan events as time-ordered records
    - Status-based classification: Classify as FOUND or LOST states
    - Family-unit lookup: Integrated lookup of family members' scan records
    - Real-time data: Used by monitoring service for latest status determination
    """
    def __init__(self, db: Session):
        """Initialize repositories needed for scan log management"""
        self.db = db
        self.scan_log_repository = ScanLogRepository(db)
        self.item_repository = ItemRepository(db)
        self.user_device_repository = UserDeviceRepository(db)
        self.family_member_repository = FamilyMemberRepository(db)

    def create_scan_log(self, user_id: int, item_id: int, status: ScanStatus) -> ScanLogResponse:
        validate_positive_int(user_id, "user_id")

        user_device = self.user_device_repository.find_by_user_id(user_id)
        if not user_device:
            raise NotFoundException("Cannot find user device")

        item = self.item_repository.get_by_id(item_id)
        if not item or not item.is_active:
            raise NotFoundException("Cannot find item")

        if item.user_device_id != user_device.id:
            raise ForbiddenException("Not your own item")

        # Additional permission check: family_id comparison
        current_user_family = self.family_member_repository.find_by_user_id(user_id)
        if not current_user_family:
            raise ForbiddenException("Not a family member")

        item_owner_family = self.family_member_repository.find_by_user_id(item.user_device.user_id)
        if not item_owner_family or current_user_family.family_id != item_owner_family.family_id:
            raise ForbiddenException("No access permission to other family's items")

        try:
            scan_log = self.scan_log_repository.create(
                user_device_id=user_device.id,
                item_id=item_id,
                status=status
            )
            self.db.commit()
            self.db.refresh(scan_log)
            return ScanLogResponse(
                id=scan_log.id,
                user_device_id=scan_log.user_device_id,
                item_id=scan_log.item_id,
                status=ScanStatus(scan_log.status),
                scanned_at=scan_log.scanned_at
            )
        except Exception:
            self.db.rollback()
            raise
