"""
Label (tag) lookup service

Service that queries physical tag (master tag) information available in RFID system.
Provides list of linkable tags when user registers new items.

Main features:
- Query available master tag list registered to user device
- Filter already connected tags (exclude tags in use)
- Provide tag UID and registration time information

Business rules:
- Users can only query tags from their own registered devices
- Only tags not connected to active items are shown as available
- Tags are physical RFID tags managed in master tag table

Usage scenarios:
1. User requests available tag list when registering new item
2. System returns unused tags registered to user's device
3. User selects desired tag to connect with item
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
    Label (master tag) lookup service class

    Provides list of physical RFID tags that users can use when registering items.
    Validates device ownership and tag usage status to return only appropriate tags.
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
            raise NotFoundException("User device not found")

        all_master_tags = self.master_tag_repository.get_all_by_device_id(user_device.device_id)
        used_tag_uids = self.item_repository.get_used_tag_uids_by_user_device_id(user_device.id)

        available_label_ids = []
        for master_tag in all_master_tags:
            if master_tag.tag_uid not in used_tag_uids:
                available_label_ids.append(master_tag.label_id)

        available_label_ids.sort()

        return AvailableLabelResponse(available_labels=available_label_ids)
