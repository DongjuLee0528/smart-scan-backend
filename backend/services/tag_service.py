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
    스마트 태그 관리 서비스

    사용자가 소유하는 가상 태그의 생성, 수정, 삭제를 관리한다.
    실제 물리적 태그와 연결되기 전 단계의 가상 태그로, 나중에 아이템과 연결되어 위치 추적이 가능해진다.

    설계 의도:
    - 사용자별 태그 소유권: 각 사용자가 자신의 태그만 관리 가능
    - 가족 단위 조회: 가족 구성원들의 태그 목록 통합 조회
    - 고유 식별자: tag_uid를 통한 물리적 태그와의 연결 준비
    - 활성 상태 관리: 소프트 삭제를 통한 데이터 보존
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
        새로운 가상 태그 생성 또는 비활성 태그 재활성화

        사용자가 새로운 태그를 등록하거나 기존 비활성 태그를 재활성화한다.
        태그 UID가 이미 존재하는 경우 소유권과 가족 소속을 확인하여 처리한다.

        Args:
            user_id: 요청 사용자 ID
            tag_uid: 물리적 태그의 고유 식별자
            name: 태그 이름
            owner_user_id: 태그 소유자 사용자 ID
            device_id: 연결할 디바이스 ID

        Returns:
            TagResponse: 생성된 태그 정보

        Raises:
            ConflictException: 태그가 다른 가족에 이미 등록되었거나 활성 상태인 경우
            NotFoundException: 사용자, 소유자, 또는 디바이스를 찾을 수 없는 경우
            BadRequestException: 가족 소속 검증 실패
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
        가족 태그 목록 조회

        사용자가 속한 가족의 모든 활성 태그를 조회한다.
        가족 구성원들의 태그를 모두 볼 수 있어 위치 추적에 활용할 수 있다.

        Args:
            user_id: 요청 사용자 ID

        Returns:
            TagListResponse: 가족 태그 목록과 총 개수

        Raises:
            NotFoundException: 사용자를 찾을 수 없는 경우
            BadRequestException: 가족 소속 검증 실패
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
        기존 태그 정보 수정

        태그의 이름, 소유자, 연결 디바이스를 변경한다.
        가족 내에서만 소유권 변경이 가능하며, 디바이스도 가족 소유여야 한다.

        Args:
            tag_id: 수정할 태그 ID
            user_id: 요청 사용자 ID
            name: 새로운 태그 이름 (선택사항)
            owner_user_id: 새로운 소유자 사용자 ID (선택사항)
            device_id: 새로운 디바이스 ID (선택사항)

        Returns:
            TagResponse: 수정된 태그 정보

        Raises:
            NotFoundException: 태그, 사용자, 소유자, 또는 디바이스를 찾을 수 없는 경우
            ForbiddenException: 가족 소속 태그가 아닌 경우
            BadRequestException: 가족 소속 검증 실패
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
        태그 소프트 삭제

        태그를 비활성화하여 숨김 처리한다.
        물리적 삭제가 아닌 소프트 삭제로 데이터를 보존한다.

        Args:
            tag_id: 삭제할 태그 ID
            user_id: 요청 사용자 ID

        Returns:
            bool: 삭제 성공 여부

        Raises:
            NotFoundException: 태그 또는 사용자를 찾을 수 없는 경우
            ForbiddenException: 가족 소속 태그가 아닌 경우
            BadRequestException: 가족 소속 검증 실패
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
        요청 사용자와 가족 구성원 정보 조회

        사용자 존재 여부와 가족 소속을 검증한다.

        Args:
            user_id: 사용자 ID

        Returns:
            tuple: (사용자 객체, 가족구성원 객체)

        Raises:
            NotFoundException: 사용자를 찾을 수 없는 경우
            BadRequestException: 가족에 소속되지 않은 경우
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
        가족 내 소유자 검증

        지정된 소유자가 동일한 가족에 속해 있는지 확인한다.

        Args:
            owner_user_id: 소유자 사용자 ID
            family_id: 가족 ID

        Returns:
            User: 검증된 소유자 객체

        Raises:
            NotFoundException: 소유자를 찾을 수 없는 경우
            BadRequestException: 다른 가족에 속한 사용자인 경우
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
        가족 소유 디바이스 검증

        지정된 디바이스가 해당 가족에 속해 있는지 확인한다.

        Args:
            device_id: 디바이스 ID
            family_id: 가족 ID

        Returns:
            Device: 검증된 디바이스 객체

        Raises:
            NotFoundException: 디바이스를 찾을 수 없는 경우
            BadRequestException: 가족 소유가 아닌 디바이스인 경우
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
        접근 가능한 활성 태그 검증

        태그가 존재하고 활성 상태이며 가족 소속인지 확인한다.

        Args:
            tag_id: 태그 ID
            family_id: 가족 ID

        Returns:
            Tag: 검증된 태그 객체

        Raises:
            NotFoundException: 태그를 찾을 수 없거나 비활성 상태인 경우
            ForbiddenException: 가족 소속 태그가 아닌 경우
        """
        tag = self.tag_repository.find_by_id(tag_id)
        if not tag or not tag.is_active:
            raise NotFoundException("Tag not found")

        if tag.family_id != family_id:
            raise ForbiddenException("Tag is not accessible in this family")

        return tag
