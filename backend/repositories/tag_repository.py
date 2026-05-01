"""
Virtual tag data access layer

Repository responsible for database operations on virtual tags created by users.
Virtual tags manage tag information before being connected to actual physical RFID tags.

Data management:
- Virtual tag creation, modification, deletion
- Mapping to physical tags through tag UID
- User-specific tag ownership management
- Tag metadata storage (name, description, color, etc.)

Business rules:
- Tag UID must be unique throughout entire system
- Users can only manage tags they created
- Family members can view each other's tags (read-only)
- Must check for associated items when deleting tags

Main query patterns:
- Tag lookup by tag UID (used when connecting physical tags)
- Tag list lookup by user (ownership-based)
- Tag list lookup by family (shared access)
- Tag filtering by status (active/inactive)
"""

from typing import Optional

from sqlalchemy.orm import Session, joinedload

from backend.models.tag import Tag


class TagRepository:
    """
    Virtual tag data access class

    Provides CRUD operations and tag management business logic for tag table.
    """
    def __init__(self, db: Session):
        """Inject database session"""
        self.db = db

    def find_by_id(self, tag_id: int) -> Optional[Tag]:
        """Find by tag ID"""
        return self.db.query(Tag).filter(Tag.id == tag_id).first()

    def find_by_tag_uid(self, tag_uid: str) -> Optional[Tag]:
        """Find by tag UID (used when connecting physical tags)"""
        return self.db.query(Tag).filter(Tag.tag_uid == tag_uid).first()

    def find_active_by_family_id(self, family_id: int) -> list[Tag]:
        """Find active tag list of family (includes owner info)"""
        return self.db.query(Tag).options(
            joinedload(Tag.owner)
        ).filter(
            Tag.family_id == family_id,
            Tag.is_active.is_(True)
        ).order_by(Tag.created_at.desc()).all()

    def find_active_by_family_id_and_owner_user_id(self, family_id: int, owner_user_id: int) -> list[Tag]:
        """Find active tag list of specific owner"""
        return self.db.query(Tag).options(
            joinedload(Tag.owner)
        ).filter(
            Tag.family_id == family_id,
            Tag.owner_user_id == owner_user_id,
            Tag.is_active.is_(True)
        ).order_by(Tag.created_at.desc()).all()

    def create(
        self,
        tag_uid: str,
        name: str,
        family_id: int,
        owner_user_id: int,
        device_id: int
    ) -> Tag:
        """Create new virtual tag"""
        tag = Tag(
            tag_uid=tag_uid,
            name=name,
            family_id=family_id,
            owner_user_id=owner_user_id,
            device_id=device_id,
            is_active=True
        )
        self.db.add(tag)
        self.db.flush()
        return tag

    def update(
        self,
        tag: Tag,
        name: str | None = None,
        owner_user_id: int | None = None,
        device_id: int | None = None,
        is_active: bool | None = None
    ) -> Tag:
        """Update tag info (modify only optional fields)"""
        if name is not None:
            tag.name = name
        if owner_user_id is not None:
            tag.owner_user_id = owner_user_id
        if device_id is not None:
            tag.device_id = device_id
        if is_active is not None:
            tag.is_active = is_active
        self.db.flush()
        return tag

    def soft_delete(self, tag: Tag) -> Tag:
        """Deactivate tag (soft delete)"""
        tag.is_active = False
        self.db.flush()
        return tag