from typing import Optional

from sqlalchemy.orm import Session

from backend.common.exceptions import BadRequestException, ConflictException, ForbiddenException, NotFoundException
from backend.common.validator import validate_positive_int, validate_serial_number
from backend.repositories.device_repository import DeviceRepository
from backend.repositories.family_member_repository import FamilyMemberRepository
from backend.repositories.item_repository import ItemRepository
from backend.repositories.scan_log_repository import ScanLogRepository
from backend.repositories.user_device_repository import UserDeviceRepository
from backend.repositories.user_repository import UserRepository
from backend.schemas.device_schema import UserDeviceResponse


class DeviceService:
    """
    Smart Scan device management service

    Handles registration, connection, and disconnection of scanner devices used by families.
    One device per family is allowed, and all family members share the device.

    Design principles:
    - Family-shared device: One scanner for joint use by a family
    - Serial number-based registration: 1:1 mapping with physical devices
    - Data protection: Devices with scan logs or items cannot be unlinked
    - Auto member connection: All family members are automatically connected when device is registered
    """
    def __init__(self, db: Session):
        """Initialize all repositories needed for device management"""
        self.db = db
        self.user_repo = UserRepository(db)
        self.device_repo = DeviceRepository(db)
        self.family_member_repo = FamilyMemberRepository(db)
        self.user_device_repo = UserDeviceRepository(db)
        self.item_repo = ItemRepository(db)
        self.scan_log_repo = ScanLogRepository(db)

    def register_device(self, user_id: int, serial_number: str) -> UserDeviceResponse:
        """
        Register scanner device to family

        Finds device by serial number and registers it to the requester's family.
        When registered, all family members are automatically connected to enable shared use.
        Only one device per family is allowed, and devices already registered to other families cannot be registered.
        """
        validate_positive_int(user_id, "user_id")
        validate_serial_number(serial_number)

        # Verify user information and family membership
        user, family_member = self._get_user_and_family_member(user_id)
        normalized_serial_number = serial_number.strip()

        # Check device existence by serial number
        device = self.device_repo.find_by_serial_number(normalized_serial_number)
        if not device:
            raise NotFoundException("Device not found")

        # Check family's existing device registration status
        family_device = self.device_repo.find_by_family_id(family_member.family_id)
        if family_device and family_device.id != device.id:
            raise ConflictException("Family already has a registered device")

        # Check if device is already registered to another family
        if device.family_id is not None and device.family_id != family_member.family_id:
            raise ForbiddenException("Device is already registered to another family")

        try:
            # Assign device to family (only if unassigned)
            if device.family_id is None:
                self.device_repo.assign_family(device, family_member.family_id)

            # Connect device to all family members (prevent duplicate connections)
            family_members = self.family_member_repo.find_all_by_family_id(family_member.family_id)
            for member in family_members:
                existing_user_device = self.user_device_repo.find_by_user_and_device(member.user_id, device.id)
                if existing_user_device:
                    continue
                self.user_device_repo.create(member.user_id, device.id)

            self.db.commit()
            user_device = self.user_device_repo.find_by_user_and_device(user.id, device.id)
            if not user_device:
                raise NotFoundException("Registered device link not found")
            return UserDeviceResponse.model_validate(user_device)
        except Exception:
            self.db.rollback()
            raise

    def get_my_device(self, user_id: int) -> Optional[UserDeviceResponse]:
        """
        Get my family's registered device information

        Returns device information if the user's family has a registered device.
        Returns None if no device is registered to the family or user is not in a family.
        """
        validate_positive_int(user_id, "user_id")

        # Query user and family information (returns None if not exists)
        user, family_member = self._find_user_and_family_member(user_id)
        if not user or not family_member:
            return None

        # Query device registered to the family
        family_device = self.device_repo.find_by_family_id(family_member.family_id)
        if not family_device:
            return None

        # Query user-device connection information
        user_device = self.user_device_repo.find_by_user_and_device(user.id, family_device.id)
        if not user_device:
            return None

        return UserDeviceResponse.model_validate(user_device)

    def unlink_device(self, user_id: int) -> bool:
        """
        Unlink family device connection

        Completely unlinks the device registered to the family.
        Unlink is blocked if scan logs or items exist to protect data.
        When unlinked, all family members' connections are removed and device becomes unassigned.
        """
        validate_positive_int(user_id, "user_id")

        # Check user's family information and registered device
        _, family_member = self._find_user_and_family_member(user_id)
        if not family_member:
            return False

        family_device = self.device_repo.find_by_family_id(family_member.family_id)
        if not family_device:
            return False

        # Query all user-device connections
        user_devices = self.user_device_repo.find_all_by_device_id(family_device.id)

        # Check data existence (block unlink if scan logs or items exist)
        for user_device in user_devices:
            if self.scan_log_repo.exists_by_user_device_id(user_device.id):
                raise BadRequestException("Scan logs exist for this device. Unlink is blocked.")

            if self.item_repo.exists_by_user_device_id(user_device.id):
                raise BadRequestException("Items exist for this device. Unlink is blocked.")

        try:
            # Delete all user-device connections then clear device family assignment
            self.user_device_repo.delete_many(user_devices)
            self.device_repo.clear_family(family_device)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def _get_user_and_family_member(self, user_id: int):
        """Query user and family member information (required - raises exception if not found)"""
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")

        family_member = self.family_member_repo.find_by_user_id(user.id)
        if not family_member:
            raise BadRequestException("User is not assigned to a family")

        return user, family_member

    def _find_user_and_family_member(self, user_id: int):
        """Query user and family member information (optional - returns None if not found)"""
        user = self.user_repo.find_by_id(user_id)
        if not user:
            return None, None

        # Query family member information (returns user info even if no family member)
        family_member = self.family_member_repo.find_by_user_id(user.id)
        if not family_member:
            return user, None

        return user, family_member
