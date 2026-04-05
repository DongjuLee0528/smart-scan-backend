from typing import Optional

from sqlalchemy.orm import Session, joinedload

from backend.models.tag import Tag


class TagRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_id(self, tag_id: int) -> Optional[Tag]:
        return self.db.query(Tag).filter(Tag.id == tag_id).first()

    def find_by_tag_uid(self, tag_uid: str) -> Optional[Tag]:
        return self.db.query(Tag).filter(Tag.tag_uid == tag_uid).first()

    def find_active_by_family_id(self, family_id: int) -> list[Tag]:
        return self.db.query(Tag).options(
            joinedload(Tag.owner)
        ).filter(
            Tag.family_id == family_id,
            Tag.is_active.is_(True)
        ).order_by(Tag.created_at.desc()).all()

    def find_active_by_family_id_and_owner_user_id(self, family_id: int, owner_user_id: int) -> list[Tag]:
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
        tag.is_active = False
        self.db.flush()
        return tag
