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
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.device_repo = DeviceRepository(db)
        self.family_member_repo = FamilyMemberRepository(db)
        self.user_device_repo = UserDeviceRepository(db)
        self.item_repo = ItemRepository(db)
        self.scan_log_repo = ScanLogRepository(db)

    def register_device(self, user_id: int, serial_number: str) -> UserDeviceResponse:
        validate_positive_int(user_id, "user_id")
        validate_serial_number(serial_number)

        user, family_member = self._get_user_and_family_member(user_id)
        normalized_serial_number = serial_number.strip()

        device = self.device_repo.find_by_serial_number(normalized_serial_number)
        if not device:
            raise NotFoundException("Device not found")

        family_device = self.device_repo.find_by_family_id(family_member.family_id)
        if family_device and family_device.id != device.id:
            raise ConflictException("Family already has a registered device")

        if device.family_id is not None and device.family_id != family_member.family_id:
            raise ForbiddenException("Device is already registered to another family")

        try:
            if device.family_id is None:
                self.device_repo.assign_family(device, family_member.family_id)

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
        validate_positive_int(user_id, "user_id")

        user, family_member = self._find_user_and_family_member(user_id)
        if not user or not family_member:
            return None

        family_device = self.device_repo.find_by_family_id(family_member.family_id)
        if not family_device:
            return None

        user_device = self.user_device_repo.find_by_user_and_device(user.id, family_device.id)
        if not user_device:
            return None

        return UserDeviceResponse.model_validate(user_device)

    def unlink_device(self, user_id: int) -> bool:
        validate_positive_int(user_id, "user_id")

        _, family_member = self._find_user_and_family_member(user_id)
        if not family_member:
            return False

        family_device = self.device_repo.find_by_family_id(family_member.family_id)
        if not family_device:
            return False

        user_devices = self.user_device_repo.find_all_by_device_id(family_device.id)

        for user_device in user_devices:
            if self.scan_log_repo.exists_by_user_device_id(user_device.id):
                raise BadRequestException("Scan logs exist for this device. Unlink is blocked.")

            if self.item_repo.exists_by_user_device_id(user_device.id):
                raise BadRequestException("Items exist for this device. Unlink is blocked.")

        try:
            self.user_device_repo.delete_many(user_devices)
            self.device_repo.clear_family(family_device)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def _get_user_and_family_member(self, user_id: int):
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")

        family_member = self.family_member_repo.find_by_user_id(user.id)
        if not family_member:
            raise BadRequestException("User is not assigned to a family")

        return user, family_member

    def _find_user_and_family_member(self, user_id: int):
        user = self.user_repo.find_by_id(user_id)
        if not user:
            return None, None

        family_member = self.family_member_repo.find_by_user_id(user.id)
        if not family_member:
            return user, None

        return user, family_member
