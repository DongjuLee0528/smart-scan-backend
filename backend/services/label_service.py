"""
라벨(태그) 조회 서비스

RFID 시스템에서 사용 가능한 물리적 태그(마스터 태그) 정보를 조회하는 서비스입니다.
사용자가 새로운 아이템을 등록할 때 연결 가능한 태그 목록을 제공합니다.

주요 기능:
- 사용자 디바이스에 등록된 사용 가능한 마스터 태그 목록 조회
- 이미 아이템과 연결된 태그 필터링 (사용 중인 태그 제외)
- 태그 UID와 등록 시간 정보 제공

비즈니스 규칙:
- 사용자는 본인이 등록한 디바이스의 태그만 조회 가능
- 활성 아이템과 연결되지 않은 태그만 사용 가능으로 표시
- 태그는 마스터 태그 테이블에서 관리되는 물리적 RFID 태그

사용 시나리오:
1. 사용자가 새 아이템 등록 시 사용 가능한 태그 목록 요청
2. 시스템이 해당 사용자의 디바이스에 등록된 미사용 태그 반환
3. 사용자가 원하는 태그를 선택하여 아이템과 연결
"""

from sqlalchemy.orm import Session

from backend.common.exceptions import NotFoundException
from backend.common.validator import validate_positive_int
from backend.repositories.item_repository import ItemRepository
from backend.repositories.master_tag_repository import MasterTagRepository
from backend.repositories.user_device_repository import UserDeviceRepository
from backend.schemas.label_schema import AvailableLabelResponse


class LabelService:
    """
    라벨(마스터 태그) 조회 서비스 클래스

    사용자가 아이템 등록 시 사용할 수 있는 물리적 RFID 태그 목록을 제공합니다.
    디바이스 소유권과 태그 사용 상태를 검증하여 적절한 태그만 반환합니다.
    """
    def __init__(self, db: Session):
        self.db = db
        self.master_tag_repository = MasterTagRepository(db)
        self.item_repository = ItemRepository(db)
        self.user_device_repository = UserDeviceRepository(db)

    def get_available_labels(self, user_id: int) -> AvailableLabelResponse:
        validate_positive_int(user_id, "user_id")

        user_device = self.user_device_repository.find_by_user_id(user_id)
        if not user_device:
            raise NotFoundException("사용자 기기를 찾을 수 없습니다")

        all_master_tags = self.master_tag_repository.get_all_by_device_id(user_device.device_id)
        used_tag_uids = self.item_repository.get_used_tag_uids_by_user_device_id(user_device.id)

        available_label_ids = []
        for master_tag in all_master_tags:
            if master_tag.tag_uid not in used_tag_uids:
                available_label_ids.append(master_tag.label_id)

        available_label_ids.sort()

        return AvailableLabelResponse(available_labels=available_label_ids)
