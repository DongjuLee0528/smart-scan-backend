from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from typing import List, Optional, Set, Tuple
from backend.models.device import Device
from backend.models.item import Item
from backend.models.master_tag import MasterTag
from backend.models.user_device import UserDevice


class ItemRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active_items_by_user_device_id(self, user_device_id: int) -> List[Item]:
        stmt = select(Item).where(
            and_(
                Item.user_device_id == user_device_id,
                Item.is_active == True
            )
        ).order_by(Item.created_at.desc())
        return self.db.execute(stmt).scalars().all()

    def get_active_items_by_user_device_ids(self, user_device_ids: List[int]) -> List[Item]:
        if not user_device_ids:
            return []

        stmt = select(Item).where(
            and_(
                Item.user_device_id.in_(user_device_ids),
                Item.is_active == True
            )
        ).order_by(Item.created_at.desc(), Item.id.desc())
        return self.db.execute(stmt).scalars().all()

    def get_active_items_with_label_by_user_device_id(self, user_device_id: int) -> List[Tuple[Item, int]]:
        stmt = select(Item, MasterTag.label_id).join(
            MasterTag,
            Item.tag_uid == MasterTag.tag_uid
        ).where(
            and_(
                Item.user_device_id == user_device_id,
                Item.is_active == True
            )
        ).order_by(Item.created_at.desc())
        return self.db.execute(stmt).all()

    def get_by_id(self, item_id: int) -> Optional[Item]:
        stmt = select(Item).where(Item.id == item_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_user_device_and_tag_uid(self, user_device_id: int, tag_uid: str) -> Optional[Item]:
        stmt = select(Item).where(
            and_(
                Item.user_device_id == user_device_id,
                Item.tag_uid == tag_uid,
                Item.is_active == True
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_family_id_and_tag_uid(
        self,
        family_id: int,
        tag_uid: str,
        exclude_item_id: Optional[int] = None
    ) -> Optional[Item]:
        stmt = select(Item).join(
            UserDevice,
            Item.user_device_id == UserDevice.id
        ).join(
            Device,
            UserDevice.device_id == Device.id
        ).where(
            and_(
                Device.family_id == family_id,
                Item.tag_uid == tag_uid,
                Item.is_active == True
            )
        ).order_by(Item.created_at.desc(), Item.id.desc())

        if exclude_item_id is not None:
            stmt = stmt.where(Item.id != exclude_item_id)

        return self.db.execute(stmt).scalars().first()

    def get_used_tag_uids_by_user_device_id(self, user_device_id: int) -> Set[str]:
        stmt = select(Item.tag_uid).where(
            and_(
                Item.user_device_id == user_device_id,
                Item.is_active == True
            )
        )
        result = self.db.execute(stmt).scalars().all()
        return set(result)

    def exists_by_user_device_id(self, user_device_id: int) -> bool:
        stmt = select(Item.id).where(Item.user_device_id == user_device_id).limit(1)
        return self.db.execute(stmt).scalar_one_or_none() is not None

    def create(self, user_device_id: int, name: str, tag_uid: str) -> Item:
        item = Item(
            user_device_id=user_device_id,
            name=name,
            tag_uid=tag_uid,
            is_active=True
        )
        self.db.add(item)
        self.db.flush()
        return item

    def update(self, item: Item, name: Optional[str] = None, tag_uid: Optional[str] = None) -> Item:
        if name is not None:
            item.name = name
        if tag_uid is not None:
            item.tag_uid = tag_uid
        self.db.flush()
        return item

    def soft_delete(self, item: Item) -> Item:
        item.is_active = False
        self.db.flush()
        return item