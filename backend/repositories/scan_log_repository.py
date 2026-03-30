from sqlalchemy.orm import Session
from backend.models.scan_log import ScanLog
from backend.schemas.scan_log_schema import ScanStatus
from datetime import datetime


class ScanLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_device_id: int, item_id: int, status: ScanStatus) -> ScanLog:
        scan_log = ScanLog(
            user_device_id=user_device_id,
            item_id=item_id,
            status=status.value,
            scanned_at=datetime.now()
        )
        self.db.add(scan_log)
        self.db.commit()
        self.db.refresh(scan_log)
        return scan_log