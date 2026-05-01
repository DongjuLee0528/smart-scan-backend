from sqlalchemy.orm import Session
from sqlalchemy import select, text
from backend.models.scan_log import ScanLog
from backend.schemas.scan_log_schema import ScanStatus


class ScanLogRepository:
    """
    Scan log data access layer

    Handles database operations for scan event logs.
    Performs FOUND/LOST status scan record storage, latest scan log lookup, item-specific scan history management, etc.

    Main responsibilities:
    - Scan event log storage and lookup
    - Latest scan status tracking per item
    - Family-unit scan log aggregation
    - Latest status information for monitoring
    """
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

        # Direct query of only 1 latest scan log per item_id using DISTINCT ON (item_id).
        # Previous approach loaded all scan_logs for given item_ids then filtered in Python,
        # causing unnecessary full scans + N+1 performance issues as item_ids increased.
        # PostgreSQL DISTINCT ON returns only first row per group based on ORDER BY,
        # allowing efficient retrieval of latest log per item with single query.
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
