from sqlalchemy.orm import Session
from backend.repositories.item_repository import ItemRepository
from backend.repositories.master_tag_repository import MasterTagRepository
from backend.repositories.user_device_repository import UserDeviceRepository
from backend.schemas.item_schema import ItemResponse, ItemListResponse
from backend.common.exceptions import NotFoundException, BadRequestException, ForbiddenException


class ItemService:
    def __init__(self, db: Session):
        self.db = db
        self.item_repository = ItemRepository(db)
        self.master_tag_repository = MasterTagRepository(db)
        self.user_device_repository = UserDeviceRepository(db)

    def get_items(self, kakao_user_id: str) -> ItemListResponse:
        user_device = self.user_device_repository.get_by_kakao_user_id(kakao_user_id)
        if not user_device:
            raise NotFoundException("사용자 기기를 찾을 수 없습니다")

        items_with_labels = self.item_repository.get_active_items_with_label_by_user_device_id(user_device.id)

        item_responses = []
        for item, label_id in items_with_labels:
            item_response = ItemResponse(
                id=item.id,
                name=item.name,
                label_id=label_id,
                created_at=item.created_at,
                updated_at=item.updated_at,
                is_active=item.is_active
            )
            item_responses.append(item_response)

        return ItemListResponse(
            items=item_responses,
            total_count=len(item_responses)
        )

    def add_item(self, kakao_user_id: str, name: str, label_id: int) -> ItemResponse:
        user_device = self.user_device_repository.get_by_kakao_user_id(kakao_user_id)
        if not user_device:
            raise NotFoundException("사용자 기기를 찾을 수 없습니다")

        master_tag = self.master_tag_repository.get_by_label_id_and_device_id(
            label_id, user_device.device_id
        )
        if not master_tag:
            raise NotFoundException("해당 라벨을 찾을 수 없습니다")

        existing_item = self.item_repository.get_by_user_device_and_tag_uid(
            user_device.id, master_tag.tag_uid
        )
        if existing_item:
            raise BadRequestException("이미 사용 중인 라벨입니다")

        try:
            item = self.item_repository.create(
                user_device_id=user_device.id,
                name=name,
                tag_uid=master_tag.tag_uid
            )
            self.db.commit()
            self.db.refresh(item)
            return ItemResponse(
                id=item.id,
                name=item.name,
                label_id=label_id,
                created_at=item.created_at,
                updated_at=item.updated_at,
                is_active=item.is_active
            )
        except Exception:
            self.db.rollback()
            raise

    def update_item(self, item_id: int, kakao_user_id: str, name: str = None, label_id: int = None) -> ItemResponse:
        user_device = self.user_device_repository.get_by_kakao_user_id(kakao_user_id)
        if not user_device:
            raise NotFoundException("사용자 기기를 찾을 수 없습니다")

        item = self.item_repository.get_by_id(item_id)
        if not item or not item.is_active:
            raise NotFoundException("물품을 찾을 수 없습니다")

        if item.user_device_id != user_device.id:
            raise ForbiddenException("본인 소유 물품이 아닙니다")

        new_tag_uid = None
        current_master_tag = self.master_tag_repository.get_by_tag_uid_and_device_id(item.tag_uid, user_device.device_id)
        if not current_master_tag:
            raise NotFoundException("연결된 라벨 정보를 찾을 수 없습니다")
        response_label_id = current_master_tag.label_id

        if label_id is not None:
            master_tag = self.master_tag_repository.get_by_label_id_and_device_id(
                label_id, user_device.device_id
            )
            if not master_tag:
                raise NotFoundException("해당 라벨을 찾을 수 없습니다")

            if master_tag.tag_uid != item.tag_uid:
                existing_item = self.item_repository.get_by_user_device_and_tag_uid(
                    user_device.id, master_tag.tag_uid
                )
                if existing_item:
                    raise BadRequestException("이미 사용 중인 라벨입니다")

                new_tag_uid = master_tag.tag_uid
                response_label_id = label_id

        try:
            updated_item = self.item_repository.update(
                item=item,
                name=name,
                tag_uid=new_tag_uid
            )
            self.db.commit()
            self.db.refresh(updated_item)
            return ItemResponse(
                id=updated_item.id,
                name=updated_item.name,
                label_id=response_label_id,
                created_at=updated_item.created_at,
                updated_at=updated_item.updated_at,
                is_active=updated_item.is_active
            )
        except Exception:
            self.db.rollback()
            raise

    def delete_item(self, item_id: int, kakao_user_id: str) -> bool:
        user_device = self.user_device_repository.get_by_kakao_user_id(kakao_user_id)
        if not user_device:
            raise NotFoundException("사용자 기기를 찾을 수 없습니다")

        item = self.item_repository.get_by_id(item_id)
        if not item or not item.is_active:
            raise NotFoundException("물품을 찾을 수 없습니다")

        if item.user_device_id != user_device.id:
            raise ForbiddenException("본인 소유 물품이 아닙니다")

        try:
            self.item_repository.soft_delete(item)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise
