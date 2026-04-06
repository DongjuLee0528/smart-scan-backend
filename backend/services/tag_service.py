from sqlalchemy.orm import Session

from backend.common.exceptions import BadRequestException, ConflictException, ForbiddenException, NotFoundException
from backend.common.validator import (
    validate_non_empty_string,
    validate_positive_int,
)
from backend.repositories.device_repository import DeviceRepository
from backend.repositories.family_member_repository import FamilyMemberRepository
from backend.repositories.tag_repository import TagRepository
from backend.repositories.user_repository import UserRepository
from backend.schemas.tag_schema import TagListResponse, TagResponse


class TagService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repository = UserRepository(db)
        self.family_member_repository = FamilyMemberRepository(db)
        self.device_repository = DeviceRepository(db)
        self.tag_repository = TagRepository(db)

    def create_tag(
        self,
        user_id: int,
        tag_uid: str,
        name: str,
        owner_user_id: int,
        device_id: int
    ) -> TagResponse:
        validate_positive_int(user_id, "user_id")
        validate_non_empty_string(tag_uid, "tag_uid")
        validate_non_empty_string(name, "name")
        validate_positive_int(owner_user_id, "owner_user_id")
        validate_positive_int(device_id, "device_id")

        normalized_tag_uid = tag_uid.strip()
        normalized_name = name.strip()

        _, family_member = self._get_actor_and_family_member(user_id)
        owner = self._get_family_owner(owner_user_id, family_member.family_id)
        device = self._get_family_device(device_id, family_member.family_id)
        existing_tag = self.tag_repository.find_by_tag_uid(normalized_tag_uid)

        try:
            if existing_tag:
                if existing_tag.family_id != family_member.family_id:
                    raise ConflictException("Tag is already registered to another family")
                if existing_tag.is_active:
                    raise ConflictException("Tag is already registered")

                tag = self.tag_repository.update(
                    existing_tag,
                    name=normalized_name,
                    owner_user_id=owner.id,
                    device_id=device.id,
                    is_active=True
                )
            else:
                tag = self.tag_repository.create(
                    tag_uid=normalized_tag_uid,
                    name=normalized_name,
                    family_id=family_member.family_id,
                    owner_user_id=owner.id,
                    device_id=device.id
                )

            self.db.commit()
            self.db.refresh(tag)
            return TagResponse.model_validate(tag)
        except Exception:
            self.db.rollback()
            raise

    def get_tags(self, user_id: int) -> TagListResponse:
        validate_positive_int(user_id, "user_id")

        _, family_member = self._get_actor_and_family_member(user_id)
        tags = self.tag_repository.find_active_by_family_id(family_member.family_id)

        return TagListResponse(
            tags=[TagResponse.model_validate(tag) for tag in tags],
            total_count=len(tags)
        )

    def update_tag(
        self,
        tag_id: int,
        user_id: int,
        name: str | None = None,
        owner_user_id: int | None = None,
        device_id: int | None = None
    ) -> TagResponse:
        validate_positive_int(tag_id, "tag_id")
        validate_positive_int(user_id, "user_id")

        if name is not None:
            validate_non_empty_string(name, "name")
        if owner_user_id is not None:
            validate_positive_int(owner_user_id, "owner_user_id")
        if device_id is not None:
            validate_positive_int(device_id, "device_id")

        _, family_member = self._get_actor_and_family_member(user_id)
        tag = self._get_accessible_tag(tag_id, family_member.family_id)

        next_owner_user_id = tag.owner_user_id
        next_device_id = tag.device_id

        if owner_user_id is not None:
            owner = self._get_family_owner(owner_user_id, family_member.family_id)
            next_owner_user_id = owner.id

        if device_id is not None:
            device = self._get_family_device(device_id, family_member.family_id)
            next_device_id = device.id

        try:
            updated_tag = self.tag_repository.update(
                tag,
                name=name.strip() if name is not None else None,
                owner_user_id=next_owner_user_id,
                device_id=next_device_id
            )
            self.db.commit()
            self.db.refresh(updated_tag)
            return TagResponse.model_validate(updated_tag)
        except Exception:
            self.db.rollback()
            raise

    def delete_tag(self, tag_id: int, user_id: int) -> bool:
        validate_positive_int(tag_id, "tag_id")
        validate_positive_int(user_id, "user_id")

        _, family_member = self._get_actor_and_family_member(user_id)
        tag = self._get_accessible_tag(tag_id, family_member.family_id)

        try:
            self.tag_repository.soft_delete(tag)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def _get_actor_and_family_member(self, user_id: int):
        actor = self.user_repository.find_by_id(user_id)
        if not actor:
            raise NotFoundException("User not found")

        family_member = self.family_member_repository.find_by_user_id(actor.id)
        if not family_member:
            raise BadRequestException("User is not assigned to a family")

        return actor, family_member

    def _get_family_owner(self, owner_user_id: int, family_id: int):
        owner = self.user_repository.find_by_id(owner_user_id)
        if not owner:
            raise NotFoundException("Owner user not found")

        family_member = self.family_member_repository.find_by_family_id_and_user_id(family_id, owner.id)
        if not family_member:
            raise BadRequestException("owner_user_id must belong to the same family")

        return owner

    def _get_family_device(self, device_id: int, family_id: int):
        device = self.device_repository.find_by_id(device_id)
        if not device:
            raise NotFoundException("Device not found")

        family_device = self.device_repository.find_by_id_and_family_id(device_id, family_id)
        if not family_device:
            raise BadRequestException("Device does not belong to the user's family")

        return family_device

    def _get_accessible_tag(self, tag_id: int, family_id: int):
        tag = self.tag_repository.find_by_id(tag_id)
        if not tag or not tag.is_active:
            raise NotFoundException("Tag not found")

        if tag.family_id != family_id:
            raise ForbiddenException("Tag is not accessible in this family")

        return tag
