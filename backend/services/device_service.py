from sqlalchemy.orm import Session
from backend.repositories.user_repository import UserRepository
from backend.repositories.device_repository import DeviceRepository
from backend.repositories.user_device_repository import UserDeviceRepository
from backend.repositories.item_repository import ItemRepository
from backend.repositories.scan_log_repository import ScanLogRepository
from backend.schemas.device_schema import UserDeviceResponse
from backend.common.exceptions import BadRequestException, NotFoundException
from backend.common.validator import validate_kakao_user_id, validate_serial_number
from typing import Optional


class DeviceService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.device_repo = DeviceRepository(db)
        self.user_device_repo = UserDeviceRepository(db)
        self.item_repo = ItemRepository(db)
        self.scan_log_repo = ScanLogRepository(db)

    def register_device(self, kakao_user_id: str, serial_number: str) -> UserDeviceResponse:
        validate_kakao_user_id(kakao_user_id)
        validate_serial_number(serial_number)

        device = self.device_repo.find_by_serial_number(serial_number)
        if not device:
            raise NotFoundException("Device not found")

        try:
            user = self.user_repo.get_or_create(kakao_user_id)

            existing_user_device = self.user_device_repo.find_by_user_and_device(user.id, device.id)
            if existing_user_device:
                return UserDeviceResponse.model_validate(existing_user_device)

            user_device = self.user_device_repo.create(user.id, device.id)
            self.db.commit()
            self.db.refresh(user_device)
            return UserDeviceResponse.model_validate(user_device)
        except Exception:
            self.db.rollback()
            raise

    def get_my_device(self, kakao_user_id: str) -> Optional[UserDeviceResponse]:
        validate_kakao_user_id(kakao_user_id)

        user = self.user_repo.find_by_kakao_user_id(kakao_user_id)
        if not user:
            return None

        user_device = self.user_device_repo.find_by_user_id(user.id)
        if not user_device:
            return None

        return UserDeviceResponse.model_validate(user_device)

    def unlink_device(self, kakao_user_id: str) -> bool:
        validate_kakao_user_id(kakao_user_id)

        user_device = self.user_device_repo.get_by_kakao_user_id(kakao_user_id)
        if not user_device:
            return False

        if self.scan_log_repo.exists_by_user_device_id(user_device.id):
            raise BadRequestException("Scan logs exist for this device. Unlink is blocked.")

        if self.item_repo.exists_by_user_device_id(user_device.id):
            raise BadRequestException("Items exist for this device. Unlink is blocked.")

        try:
            self.user_device_repo.delete(user_device)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise
