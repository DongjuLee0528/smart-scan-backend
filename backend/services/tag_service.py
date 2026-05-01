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
    """
    Smart tag management service

    Manages creation, modification, and deletion of virtual tags owned by users.
    These are virtual tags before being connected to actual physical tags, later connected to items to enable location tracking.

    Design principles:
    - User-specific tag ownership: Each user can only manage their own tags
    - Family-unit lookup: Integrated lookup of family members' tag lists
    - Unique identifier: Preparation for connection to physical tags through tag_uid
    - Active status management: Data preservation through soft deletion
    """
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
        """
        Create new virtual tag or reactivate inactive tag

        User registers new tag or reactivates existing inactive tag.
        When tag UID already exists, check ownership and family membership for processing.

        Args:
            user_id: Requester user ID
            tag_uid: Unique identifier of physical tag
            name: Tag name
            owner_user_id: Tag owner user ID
            device_id: Device ID to connect

        Returns:
            TagResponse: Created tag information

        Raises:
            ConflictException: When tag is already registered to another family or is active
            NotFoundException: When user, owner, or device cannot be found
            BadRequestException: When family membership verification fails
        """
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
        """
        Query family tag list

        Query all active tags of the family that user belongs to.
        Can view all family members' tags for use in location tracking.

        Args:
            user_id: Request user ID

        Returns:
            TagListResponse: Family tag list and total count

        Raises:
            NotFoundException: When user cannot be found
            BadRequestException: Family membership verification failure
        """
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
        """
        Modify existing tag information

        Change tag name, owner, and connected device.
        Ownership change is only possible within family, and device must also be family-owned.

        Args:
            tag_id: Tag ID to modify
            user_id: Request user ID
            name: New tag name (optional)
            owner_user_id: New owner user ID (optional)
            device_id: New device ID (optional)

        Returns:
            TagResponse: Modified tag information

        Raises:
            NotFoundException: When tag, user, owner, or device cannot be found
            ForbiddenException: When tag is not family-owned
            BadRequestException: Family membership verification failure
        """
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
        """
        Tag soft deletion

        Deactivate tag for hidden processing.
        Preserve data through soft deletion rather than physical deletion.

        Args:
            tag_id: Tag ID to delete
            user_id: Request user ID

        Returns:
            bool: Deletion success status

        Raises:
            NotFoundException: When tag or user cannot be found
            ForbiddenException: When tag is not family-owned
            BadRequestException: Family membership verification failure
        """
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
        """
        Query request user and family member information

        Verify user existence and family membership.

        Args:
            user_id: User ID

        Returns:
            tuple: (user object, family member object)

        Raises:
            NotFoundException: When user cannot be found
            BadRequestException: When user does not belong to family
        """
        actor = self.user_repository.find_by_id(user_id)
        if not actor:
            raise NotFoundException("User not found")

        family_member = self.family_member_repository.find_by_user_id(actor.id)
        if not family_member:
            raise BadRequestException("User is not assigned to a family")

        return actor, family_member

    def _get_family_owner(self, owner_user_id: int, family_id: int):
        """
        Verify owner within family

        Verify that specified owner belongs to the same family.

        Args:
            owner_user_id: Owner user ID
            family_id: Family ID

        Returns:
            User: Verified owner object

        Raises:
            NotFoundException: When owner cannot be found
            BadRequestException: When user belongs to different family
        """
        owner = self.user_repository.find_by_id(owner_user_id)
        if not owner:
            raise NotFoundException("Owner user not found")

        family_member = self.family_member_repository.find_by_family_id_and_user_id(family_id, owner.id)
        if not family_member:
            raise BadRequestException("owner_user_id must belong to the same family")

        return owner

    def _get_family_device(self, device_id: int, family_id: int):
        """
        Verify family-owned device

        Verify that specified device belongs to the family.

        Args:
            device_id: Device ID
            family_id: Family ID

        Returns:
            Device: Verified device object

        Raises:
            NotFoundException: When device cannot be found
            BadRequestException: When device is not family-owned
        """
        device = self.device_repository.find_by_id(device_id)
        if not device:
            raise NotFoundException("Device not found")

        family_device = self.device_repository.find_by_id_and_family_id(device_id, family_id)
        if not family_device:
            raise BadRequestException("Device does not belong to the user's family")

        return family_device

    def _get_accessible_tag(self, tag_id: int, family_id: int):
        """
        Verify accessible active tag

        Verify that tag exists, is active, and belongs to family.

        Args:
            tag_id: Tag ID
            family_id: Family ID

        Returns:
            Tag: Verified tag object

        Raises:
            NotFoundException: When tag cannot be found or is inactive
            ForbiddenException: When tag is not family-owned
        """
        tag = self.tag_repository.find_by_id(tag_id)
        if not tag or not tag.is_active:
            raise NotFoundException("Tag not found")

        if tag.family_id != family_id:
            raise ForbiddenException("Tag is not accessible in this family")

        return tag
