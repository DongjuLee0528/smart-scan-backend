from sqlalchemy.orm import Session
from sqlalchemy import select, text
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

    def find_latest_by_item_ids(self, item_ids: list[int]) -> dict[int, ScanLog]:
        if not item_ids:
            return {}

        # DISTINCT ON (item_id)으로 각 item_id별 최신 스캔 로그 1개만 DB에서 직접 조회.
        # 기존 방식은 해당 item_ids의 모든 scan_logs를 불러온 뒤 Python에서 필터링하여
        # item_ids 수가 많을수록 불필요한 전체 스캔 + N+1 성능 문제가 발생했음.
        # PostgreSQL DISTINCT ON은 ORDER BY 기준으로 각 그룹의 첫 번째 행만 반환하므로
        # 쿼리 1회로 item별 최신 로그를 효율적으로 가져올 수 있음.
        stmt = text("""
            SELECT DISTINCT ON (item_id)
                id, user_device_id, item_id, status, scanned_at
            FROM scan_logs
            WHERE item_id = ANY(:item_ids)
            ORDER BY item_id, scanned_at DESC, id DESC
        """)
        rows = self.db.execute(stmt, {"item_ids": item_ids}).mappings().all()

        result: dict[int, ScanLog] = {}
        for row in rows:
            scan_log = ScanLog(**dict(row))
            result[scan_log.item_id] = scan_log
        return result
