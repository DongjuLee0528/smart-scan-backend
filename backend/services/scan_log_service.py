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
    스캔 로그 관리 서비스

    사용자 디바이스에서 발생한 스캔 이벤트의 기록과 조회를 담당한다.
    FOUND/LOST 상태의 스캔 로그를 처리하여 태그 위치 추적 기반 데이터를 제공한다.

    설계 의도:
    - 위치 추적 로그: 모든 스캔 이벤트를 시간순 기록으로 저장
    - 상태 기반 분류: FOUND(발견), LOST(분실) 상태로 구분
    - 가족 단위 조회: 가족 구성원들의 스캔 기록 통합 조회
    - 실시간 데이터: 모니터링 서비스에서 최신 상태 판단에 활용
    """
    def __init__(self, db: Session):
        """스캔 로그 관리에 필요한 리포지토리 초기화"""
        self.db = db
        self.scan_log_repository = ScanLogRepository(db)
        self.item_repository = ItemRepository(db)
        self.user_device_repository = UserDeviceRepository(db)
        self.family_member_repository = FamilyMemberRepository(db)

    def create_scan_log(self, user_id: int, item_id: int, status: ScanStatus) -> ScanLogResponse:
        validate_positive_int(user_id, "user_id")

        user_device = self.user_device_repository.find_by_user_id(user_id)
        if not user_device:
            raise NotFoundException("사용자 기기를 찾을 수 없습니다")

        item = self.item_repository.get_by_id(item_id)
        if not item or not item.is_active:
            raise NotFoundException("물품을 찾을 수 없습니다")

        if item.user_device_id != user_device.id:
            raise ForbiddenException("본인 소유 물품이 아닙니다")

        # 추가 권한 체크: family_id 비교
        current_user_family = self.family_member_repository.find_by_user_id(user_id)
        if not current_user_family:
            raise ForbiddenException("가족 구성원이 아닙니다")

        item_owner_family = self.family_member_repository.find_by_user_id(item.user_device.user_id)
        if not item_owner_family or current_user_family.family_id != item_owner_family.family_id:
            raise ForbiddenException("다른 가족의 물품에 대한 접근 권한이 없습니다")

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
