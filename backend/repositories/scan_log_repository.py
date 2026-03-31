from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.models.scan_log import ScanLog
from backend.schemas.scan_log_schema import ScanStatus


class ScanLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_device_id: int, item_id: int, status: ScanStatus) -> ScanLog:
        scan_log = ScanLog(
            user_device_id=user_device_id,
            item_id=item_id,
            status=status.value
        )
        self.db.add(scan_log)
        self.db.flush()
        return scan_log

    def exists_by_user_device_id(self, user_device_id: int) -> bool:
        stmt = select(ScanLog.id).where(ScanLog.user_device_id == user_device_id).limit(1)
        return self.db.execute(stmt).scalar_one_or_none() is not None
