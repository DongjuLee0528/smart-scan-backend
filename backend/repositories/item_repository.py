from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from typing import List, Optional
from backend.models.item import Item


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

    def create(self, user_device_id: int, name: str, tag_uid: str) -> Item:
        item = Item(
            user_device_id=user_device_id,
            name=name,
            tag_uid=tag_uid,
            is_active=True
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update(self, item: Item, name: Optional[str] = None, tag_uid: Optional[str] = None) -> Item:
        if name is not None:
            item.name = name
        if tag_uid is not None:
            item.tag_uid = tag_uid
        self.db.commit()
        self.db.refresh(item)
        return item

    def soft_delete(self, item: Item) -> Item:
        item.is_active = False
        self.db.commit()
        self.db.refresh(item)
        return item