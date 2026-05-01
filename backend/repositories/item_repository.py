"""
Item data access layer

Repository responsible for database operations on real items connected to tags.
Provides item lookup, creation, modification, and deletion functions along with label information.

Data management:
- Item metadata (name, description, registration date, etc.)
- Connection to physical tags through tag UID
- Label-based item classification and lookup
- Item management per user device

Business rules:
- Only one active item can be connected to one tag UID
- Users can only modify/delete their own registered items
- Family members can view each other's items (read-only)
- Must check for associated scan logs when deleting items

Main use cases:
- Create items when users register new belongings
- Retrieve complete belonging lists of family members
- Search connected item information when tags are scanned
- Item classification and statistics by label
"""

from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from typing import List, Optional, Set, Tuple
from backend.models.device import Device
from backend.models.item import Item
from backend.models.master_tag import MasterTag
from backend.models.user_device import UserDevice


class ItemRepository:
    """
    Item data access layer

    Handles database operations for real items connected to tags.
    Provides item lookup, creation, modification, and deletion functions along with label information.

    Main responsibilities:
    - CRUD operations on item entities
    - Tag UID-based lookup and duplicate checking
    - Provide item lists connected to labels
    - Family-unit item management
    """
    def __init__(self, db: Session):
        """Inject database session"""
        self.db = db

    def get_active_items_by_user_device_id(self, user_device_id: int) -> List[Item]:
        """
        Find active item list of user device

        Args:
            user_device_id: User-device connection ID to query

        Returns:
            List[Item]: Active item list (latest registration order)
        """
        stmt = select(Item).where(
            and_(
                Item.user_device_id == user_device_id,
                Item.is_active == True
            )
        ).order_by(Item.created_at.desc())
        return self.db.execute(stmt).scalars().all()

    def get_active_items_by_user_device_ids(self, user_device_ids: List[int]) -> List[Item]:
        """
        Find active item list of multiple user devices

        Used when querying items of all family members.

        Args:
            user_device_ids: List of user-device connection IDs to query

        Returns:
            List[Item]: All active item lists (latest registration order)
        """
        if not user_device_ids:
            return []

        stmt = select(Item).where(
            and_(
                Item.user_device_id.in_(user_device_ids),
                Item.is_active == True
            )
        ).order_by(Item.created_at.desc(), Item.id.desc())
        return self.db.execute(stmt).scalars().all()

    def get_active_items_with_label_by_user_device_id(self, user_device_id: int) -> List[Tuple[Item, Optional[int]]]:
        """Find active items and label info together for user device.

        A-full: Use LEFT OUTER JOIN to include pending items (tag_uid NULL) in list.
        label_id of pending items is returned as None.
        """
        stmt = select(Item, MasterTag.label_id).outerjoin(
            MasterTag,
            Item.tag_uid == MasterTag.tag_uid
        ).where(
            and_(
                Item.user_device_id == user_device_id,
                Item.is_active == True
            )
        ).order_by(Item.created_at.desc())
        return self.db.execute(stmt).all()

    def get_active_items_by_kakao_user_id(self, kakao_user_id: str) -> List[Item]:
        """Find active item list of KakaoTalk user (includes pending).

        Dedicated for chatbot HTTP endpoint. user_device is joined with User table and filtered by kakao_user_id.
        """
        from backend.models.user import User
        from backend.models.user_device import UserDevice
        stmt = select(Item).join(
            UserDevice, Item.user_device_id == UserDevice.id
        ).join(
            User, UserDevice.user_id == User.id
        ).where(
            and_(
                User.kakao_user_id == kakao_user_id,
                Item.is_active == True
            )
        ).order_by(Item.created_at.desc())
        return self.db.execute(stmt).scalars().all()

    def get_active_by_user_device_and_name(self, user_device_id: int, name: str) -> Optional[Item]:
        """Find active item by name (chatbot name-based deletion)."""
        stmt = select(Item).where(
            and_(
                Item.user_device_id == user_device_id,
                Item.name == name,
                Item.is_active == True
            )
        ).order_by(Item.created_at.desc(), Item.id.desc())
        return self.db.execute(stmt).scalars().first()

    def get_all_active_by_user_device_id(self, user_device_id: int) -> List[Item]:
        """Return all active items of user device (batch soft-delete when unlinking device)."""
        stmt = select(Item).where(
            and_(
                Item.user_device_id == user_device_id,
                Item.is_active == True
            )
        )
        return self.db.execute(stmt).scalars().all()

    def create_pending(self, user_device_id: int, name: str) -> Item:
        """Create pending item not connected to label (add name only from chatbot)."""
        item = Item(
            user_device_id=user_device_id,
            name=name,
            tag_uid=None,
            is_active=True,
            is_pending=True
        )
        self.db.add(item)
        self.db.flush()
        return item

    def bind_tag(self, item: Item, tag_uid: str) -> Item:
        """Connect tag_uid to pending item to convert to active item."""
        item.tag_uid = tag_uid
        item.is_pending = False
        self.db.flush()
        return item

    def get_by_id(self, item_id: int) -> Optional[Item]:
        """Find by item ID"""
        stmt = select(Item).where(Item.id == item_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_user_device_and_tag_uid(self, user_device_id: int, tag_uid: str) -> Optional[Item]:
        """Find item by user device and tag UID"""
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
        """Check duplicate tag UID usage within family (can exclude self when modifying)"""
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
        """Return set of tag UIDs in use by user device"""
        stmt = select(Item.tag_uid).where(
            and_(
                Item.user_device_id == user_device_id,
                Item.is_active == True
            )
        )
        result = self.db.execute(stmt).scalars().all()
        return set(result)

    def exists_by_user_device_id(self, user_device_id: int) -> bool:
        """Check if items exist on user device"""
        stmt = select(Item.id).where(Item.user_device_id == user_device_id).limit(1)
        return self.db.execute(stmt).scalar_one_or_none() is not None

    def create(self, user_device_id: int, name: str, tag_uid: str) -> Item:
        """Create new item"""
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
        """Update item info (modify only optional fields)"""
        if name is not None:
            item.name = name
        if tag_uid is not None:
            item.tag_uid = tag_uid
        self.db.flush()
        return item

    def soft_delete(self, item: Item) -> Item:
        """Deactivate item (soft delete)"""
        item.is_active = False
        self.db.flush()
        return item