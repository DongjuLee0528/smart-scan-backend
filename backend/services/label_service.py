from sqlalchemy.orm import Session
from backend.repositories.master_tag_repository import MasterTagRepository
from backend.repositories.item_repository import ItemRepository
from backend.repositories.user_device_repository import UserDeviceRepository
from backend.schemas.label_schema import AvailableLabelResponse
from backend.common.exceptions import NotFoundException


class LabelService:
    def __init__(self, db: Session):
        self.db = db
        self.master_tag_repository = MasterTagRepository(db)
        self.item_repository = ItemRepository(db)
        self.user_device_repository = UserDeviceRepository(db)

    def get_available_labels(self, kakao_user_id: str) -> AvailableLabelResponse:
        user_device = self.user_device_repository.get_by_kakao_user_id(kakao_user_id)
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