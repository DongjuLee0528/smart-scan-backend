from sqlalchemy.orm import Session

from backend.common.exceptions import BadRequestException, ForbiddenException, NotFoundException
from backend.common.validator import validate_positive_int
from backend.repositories.item_repository import ItemRepository
from backend.repositories.master_tag_repository import MasterTagRepository
from backend.repositories.tag_repository import TagRepository
from backend.repositories.user_device_repository import UserDeviceRepository
from backend.schemas.item_schema import ItemListResponse, ItemResponse


class ItemService:
    """
    Smart tag connected item management service

    Manages registration and management of real items that users connect with tags.
    Items are linked to master tags (physical tags) and can be categorized through labels.

    Design principles:
    - Family shared items: Any family member can view items
    - Tag-item 1:1 matching: One master tag can only connect to one active item
    - Label-based categorization: Manage items by category for user convenience
    - Family device dependent: Items can only be managed through device registered to family
    """
    def __init__(self, db: Session):
        """Initialize repositories needed for item management"""
        self.db = db
        self.item_repository = ItemRepository(db)
        self.master_tag_repository = MasterTagRepository(db)
        self.user_device_repository = UserDeviceRepository(db)
        self.tag_repository = TagRepository(db)

    def get_items(self, user_id: int) -> ItemListResponse:
        """
        Retrieve all items registered to family

        Returns all active items registered to the user's family device with label information.
        Items registered by other family members are also accessible to support family sharing.
        """
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
                is_active=item.is_active,
                is_pending=item.is_pending
            )
            item_responses.append(item_response)

        return ItemListResponse(
            items=item_responses,
            total_count=len(item_responses)
        )

    def add_item(self, user_id: int, name: str, label_id: int) -> ItemResponse:
        """
        Register new item

        Register new item using master tag corresponding to user-specified label.
        Throw error if another item is already registered with same tag UID.
        """
        validate_positive_int(user_id, "user_id")
        user_device = self._get_family_registered_user_device(user_id)

        master_tag = self.master_tag_repository.get_by_label_id_and_device_id(
            label_id, user_device.device_id
        )
        if not master_tag:
            raise NotFoundException("Cannot find the specified label")

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
            self._upsert_tag_for_item(
                tag_uid=master_tag.tag_uid,
                name=name,
                user_device=user_device,
            )
            self.db.commit()
            self.db.refresh(item)
            return ItemResponse(
                id=item.id,
                name=item.name,
                label_id=label_id,
                created_at=item.created_at,
                updated_at=item.updated_at,
                is_active=item.is_active,
                is_pending=item.is_pending
            )
        except Exception:
            self.db.rollback()
            raise

    def update_item(self, item_id: int, user_id: int, name: str = None, label_id: int = None) -> ItemResponse:
        """
        Update item information

        Modify item name or label.
        When changing label, connect to different master tag and check availability of new tag UID.
        Only items registered by user can be modified.
        """
        validate_positive_int(user_id, "user_id")
        user_device = self._get_family_registered_user_device(user_id)

        item = self.item_repository.get_by_id(item_id)
        if not item or not item.is_active:
            raise NotFoundException("Cannot find item")

        if item.user_device_id != user_device.id:
            raise ForbiddenException("This is not your own item")

        if item.is_pending or item.tag_uid is None:
            raise BadRequestException("Item pending label connection must be connected to label first before modification")

        new_tag_uid = None
        current_master_tag = self.master_tag_repository.get_by_tag_uid_and_device_id(item.tag_uid, user_device.device_id)
        if not current_master_tag:
            raise NotFoundException("Cannot find connected label information")
        response_label_id = current_master_tag.label_id

        if label_id is not None:
            master_tag = self.master_tag_repository.get_by_label_id_and_device_id(
                label_id, user_device.device_id
            )
            if not master_tag:
                raise NotFoundException("Cannot find the specified label")

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
            tag_uid_to_sync = new_tag_uid if new_tag_uid else item.tag_uid
            if tag_uid_to_sync:
                self._upsert_tag_for_item(
                    tag_uid=tag_uid_to_sync,
                    name=name if name is not None else item.name,
                    user_device=user_device,
                )
            self.db.commit()
            self.db.refresh(updated_item)
            return ItemResponse(
                id=updated_item.id,
                name=updated_item.name,
                label_id=response_label_id,
                created_at=updated_item.created_at,
                updated_at=updated_item.updated_at,
                is_active=updated_item.is_active,
                is_pending=updated_item.is_pending
            )
        except Exception:
            self.db.rollback()
            raise

    def delete_item(self, item_id: int, user_id: int) -> bool:
        """
        Delete item (soft delete)

        Logically delete item by making it inactive.
        Only items registered by user can be deleted.
        """
        validate_positive_int(user_id, "user_id")
        user_device = self._get_family_registered_user_device(user_id)

        item = self.item_repository.get_by_id(item_id)
        if not item or not item.is_active:
            raise NotFoundException("Cannot find item")

        if item.user_device_id != user_device.id:
            raise ForbiddenException("This is not your own item")

        try:
            self.item_repository.soft_delete(item)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def bind_item(self, item_id: int, user_id: int, label_id: int) -> ItemResponse:
        """
        Connect label (master tag) to pending item and convert to active item

        Connect item that was added with name only (is_pending=True) from chatbot to label in web interface.
        """
        validate_positive_int(user_id, "user_id")
        user_device = self._get_family_registered_user_device(user_id)

        item = self.item_repository.get_by_id(item_id)
        if not item or not item.is_active:
            raise NotFoundException("Cannot find item")
        if item.user_device_id != user_device.id:
            raise ForbiddenException("This is not your own item")
        if not item.is_pending:
            raise BadRequestException("Item is already connected to a label")

        master_tag = self.master_tag_repository.get_by_label_id_and_device_id(
            label_id, user_device.device_id
        )
        if not master_tag:
            raise NotFoundException("Cannot find the specified label")

        self._ensure_family_tag_uid_available(
            family_id=user_device.device.family_id,
            tag_uid=master_tag.tag_uid,
            exclude_item_id=item.id
        )

        try:
            updated = self.item_repository.bind_tag(item=item, tag_uid=master_tag.tag_uid)
            self._upsert_tag_for_item(
                tag_uid=master_tag.tag_uid,
                name=item.name,
                user_device=user_device,
            )
            self.db.commit()
            self.db.refresh(updated)
            return ItemResponse(
                id=updated.id,
                name=updated.name,
                label_id=label_id,
                created_at=updated.created_at,
                updated_at=updated.updated_at,
                is_active=updated.is_active,
                is_pending=updated.is_pending
            )
        except Exception:
            self.db.rollback()
            raise

    # ---------- Chatbot-facing methods (based on kakao_user_id) ----------
    def chatbot_list_items(self, kakao_user_id: str) -> ItemListResponse:
        """Chatbot: Active item list (includes pending, label_id may be unassigned)."""
        user_device = self._get_kakao_user_device(kakao_user_id)
        items_with_labels = self.item_repository.get_active_items_with_label_by_user_device_id(user_device.id)
        responses = [
            ItemResponse(
                id=item.id,
                name=item.name,
                label_id=label_id,
                created_at=item.created_at,
                updated_at=item.updated_at,
                is_active=item.is_active,
                is_pending=item.is_pending,
            )
            for item, label_id in items_with_labels
        ]
        return ItemListResponse(items=responses, total_count=len(responses))

    def chatbot_add_pending_item(self, kakao_user_id: str, name: str) -> ItemResponse:
        """Chatbot: Add pending item with name only."""
        user_device = self._get_kakao_user_device(kakao_user_id)
        try:
            item = self.item_repository.create_pending(
                user_device_id=user_device.id,
                name=name,
            )
            self.db.commit()
            self.db.refresh(item)
            return ItemResponse(
                id=item.id,
                name=item.name,
                label_id=None,
                created_at=item.created_at,
                updated_at=item.updated_at,
                is_active=item.is_active,
                is_pending=item.is_pending,
            )
        except Exception:
            self.db.rollback()
            raise

    def chatbot_delete_by_name(self, kakao_user_id: str, name: str) -> int:
        """Chatbot: Find item by name and soft-delete. Return: number deleted (0 or 1)."""
        user_device = self._get_kakao_user_device(kakao_user_id)
        item = self.item_repository.get_active_by_user_device_and_name(user_device.id, name)
        if not item:
            return 0
        try:
            self.item_repository.soft_delete(item)
            self.db.commit()
            return 1
        except Exception:
            self.db.rollback()
            raise

    def chatbot_unlink_device(self, kakao_user_id: str) -> int:
        """Chatbot: Bulk soft-delete all active items for the user. Return: number deleted."""
        user_device = self._get_kakao_user_device(kakao_user_id)
        items = self.item_repository.get_all_active_by_user_device_id(user_device.id)
        count = 0
        try:
            for item in items:
                self.item_repository.soft_delete(item)
                count += 1
            self.db.commit()
            return count
        except Exception:
            self.db.rollback()
            raise

    def _get_kakao_user_device(self, kakao_user_id: str):
        """Query family registered device by KakaoTalk user ID (chatbot endpoint exclusive)."""
        if not kakao_user_id or not kakao_user_id.strip():
            raise BadRequestException("kakao_user_id is empty")
        user_device = self.user_device_repository.get_by_kakao_user_id(kakao_user_id.strip())
        if not user_device:
            raise NotFoundException("Cannot find connected device")
        if not user_device.device or user_device.device.family_id is None:
            raise BadRequestException("User device is not registered to family")
        return user_device

    def _get_family_registered_user_device(self, user_id: int):
        """Query user's family registered device (required verification before item management)"""
        user_device = self.user_device_repository.find_by_user_id(user_id)
        if not user_device:
            raise NotFoundException("Cannot find user device")
        if not user_device.device or user_device.device.family_id is None:
            raise BadRequestException("User device is not registered to family")
        return user_device

    def _upsert_tag_for_item(self, tag_uid: str, name: str, user_device) -> None:
        """Create or update tags record when tag_uid is set on item."""
        existing = self.tag_repository.find_by_tag_uid(tag_uid)
        if existing:
            self.tag_repository.update(
                existing,
                name=name,
                owner_user_id=user_device.user_id,
                device_id=user_device.device_id,
                is_active=True,
            )
        else:
            self.tag_repository.create(
                tag_uid=tag_uid,
                name=name,
                family_id=user_device.device.family_id,
                owner_user_id=user_device.user_id,
                device_id=user_device.device_id,
            )

    def _ensure_family_tag_uid_available(
        self,
        family_id: int,
        tag_uid: str,
        exclude_item_id: int | None = None
    ) -> None:
        """
        Validation to prevent duplicate tag UID usage within family

        Check if there are other items using the same tag UID in the same family.
        Use exclude_item_id to exclude self when modifying.
        """
        existing_item = self.item_repository.get_by_family_id_and_tag_uid(
            family_id=family_id,
            tag_uid=tag_uid,
            exclude_item_id=exclude_item_id
        )
        if existing_item:
            raise BadRequestException("Label is already in use within the family")
