from sqlalchemy.orm import Session

from backend.common.exceptions import BadRequestException, ForbiddenException, NotFoundException
from backend.common.validator import validate_positive_int
from backend.repositories.item_repository import ItemRepository
from backend.repositories.master_tag_repository import MasterTagRepository
from backend.repositories.user_device_repository import UserDeviceRepository
from backend.schemas.item_schema import ItemListResponse, ItemResponse


class ItemService:
    def __init__(self, db: Session):
        self.db = db
        self.item_repository = ItemRepository(db)
        self.master_tag_repository = MasterTagRepository(db)
        self.user_device_repository = UserDeviceRepository(db)

    def get_items(self, user_id: int) -> ItemListResponse:
        validate_positive_int(user_id, "user_id")
        user_device = self._get_family_registered_user_device(user_id)

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

    def add_item(self, user_id: int, name: str, label_id: int) -> ItemResponse:
        validate_positive_int(user_id, "user_id")
        user_device = self._get_family_registered_user_device(user_id)

        master_tag = self.master_tag_repository.get_by_label_id_and_device_id(
            label_id, user_device.device_id
        )
        if not master_tag:
            raise NotFoundException("해당 라벨을 찾을 수 없습니다")

        self._ensure_family_tag_uid_available(
            family_id=user_device.device.family_id,
            tag_uid=master_tag.tag_uid
        )

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

    def update_item(self, item_id: int, user_id: int, name: str = None, label_id: int = None) -> ItemResponse:
        validate_positive_int(user_id, "user_id")
        user_device = self._get_family_registered_user_device(user_id)

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
                self._ensure_family_tag_uid_available(
                    family_id=user_device.device.family_id,
                    tag_uid=master_tag.tag_uid,
                    exclude_item_id=item.id
                )

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

    def delete_item(self, item_id: int, user_id: int) -> bool:
        validate_positive_int(user_id, "user_id")
        user_device = self._get_family_registered_user_device(user_id)

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

    def _get_family_registered_user_device(self, user_id: int):
        user_device = self.user_device_repository.find_by_user_id(user_id)
        if not user_device:
            raise NotFoundException("사용자 기기를 찾을 수 없습니다")
        if not user_device.device or user_device.device.family_id is None:
            raise BadRequestException("사용자 기기가 가족에 등록되어 있지 않습니다")
        return user_device

    def _ensure_family_tag_uid_available(
        self,
        family_id: int,
        tag_uid: str,
        exclude_item_id: int | None = None
    ) -> None:
        existing_item = self.item_repository.get_by_family_id_and_tag_uid(
            family_id=family_id,
            tag_uid=tag_uid,
            exclude_item_id=exclude_item_id
        )
        if existing_item:
            raise BadRequestException("이미 가족 내에서 사용 중인 라벨입니다")
