from sqlalchemy.orm import Session
from backend.repositories.scan_log_repository import ScanLogRepository
from backend.repositories.item_repository import ItemRepository
from backend.repositories.user_device_repository import UserDeviceRepository
from backend.schemas.scan_log_schema import ScanLogResponse, ScanStatus
from backend.common.exceptions import NotFoundException, ForbiddenException


class ScanLogService:
    def __init__(self, db: Session):
        self.db = db
        self.scan_log_repository = ScanLogRepository(db)
        self.item_repository = ItemRepository(db)
        self.user_device_repository = UserDeviceRepository(db)

    def create_scan_log(self, kakao_user_id: str, item_id: int, status: ScanStatus) -> ScanLogResponse:
        user_device = self.user_device_repository.get_by_kakao_user_id(kakao_user_id)
        if not user_device:
            raise NotFoundException("사용자 기기를 찾을 수 없습니다")

        item = self.item_repository.get_by_id(item_id)
        if not item or not item.is_active:
            raise NotFoundException("물품을 찾을 수 없습니다")

        if item.user_device_id != user_device.id:
            raise ForbiddenException("본인 소유 물품이 아닙니다")

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
