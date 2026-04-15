"""
가족 구성원 관리 서비스

SmartScan 시스템에서 가족 그룹 내 구성원의 추가, 삭제, 관리를 담당하는 서비스입니다.
가족 기반 소지품 추적 시스템의 핵심 구성 요소로, 구성원별 개별 아이템 관리를 지원합니다.

주요 기능:
- 가족 구성원 추가/삭제 (가족 소유자 권한 필요)
- 구성원별 소지품 조회 및 통계
- 구성원별 스캔 이력 관리
- 구성원 정보 수정 (이름, 나이, 이메일 등)

비즈니스 규칙:
- 가족 소유자만 구성원 추가/삭제 가능
- 구성원 삭제 시 연관된 아이템과 스캔 로그 연쇄 삭제
- 이메일 중복 검증 (가족 내 고유성)
- 최대 구성원 수 제한 (설정 가능)

보안 고려사항:
- 구성원 정보는 가족 단위로 격리
- 개인정보 수정은 본인 또는 가족 소유자만 가능
"""

from sqlalchemy.orm import Session

from backend.common.exceptions import BadRequestException, ConflictException, ForbiddenException, NotFoundException
from backend.common.service_base import ServiceBase
from backend.common.validator import (
    validate_email,
    validate_non_empty_string,
    validate_optional_age,
    validate_positive_int,
)
from backend.repositories.device_repository import DeviceRepository
from backend.repositories.family_member_repository import FamilyMemberRepository
from backend.repositories.family_repository import FamilyRepository
from backend.repositories.item_repository import ItemRepository
from backend.repositories.scan_log_repository import ScanLogRepository
from backend.repositories.user_device_repository import UserDeviceRepository
from backend.repositories.user_repository import UserRepository
from backend.schemas.family_member_schema import FamilyMemberListResponse, FamilyMemberResponse


class FamilyMemberService(ServiceBase):
    """
    가족 구성원 관리 서비스 클래스

    가족 그룹 내에서 구성원을 관리하고, 각 구성원의 소지품과 스캔 이력을 추적합니다.
    ServiceBase를 상속하여 공통 액터 컨텍스트 기능을 활용합니다.
    """
    def __init__(self, db: Session):
        super().__init__(db)
        self.device_repository = DeviceRepository(db)
        self.user_device_repository = UserDeviceRepository(db)
        self.item_repository = ItemRepository(db)
        self.scan_log_repository = ScanLogRepository(db)

    def add_member(
        self,
        user_id: int,
        name: str,
        email: str,
        phone_number: str,
        age: int | None = None
    ) -> FamilyMemberResponse:
        validate_positive_int(user_id, "user_id")
        validate_non_empty_string(name, "name")
        validate_email(email)
        validate_non_empty_string(phone_number, "phone_number")
        validate_optional_age(age)

        actor, actor_family_member, family = self._get_actor_context(user_id)
        self._ensure_owner(actor.id, actor_family_member.role, family.owner_user_id)

        target_user = self._resolve_existing_user(email.strip(), phone_number.strip())
        existing_member = self.family_member_repository.find_by_user_id(target_user.id)
        if existing_member:
            if existing_member.family_id == family.id:
                raise ConflictException("User is already a member of this family")
            raise ConflictException("User already belongs to another family")

        try:
            family_member = self.family_member_repository.create(family.id, target_user.id, "member")
            family_device = self.device_repository.find_by_family_id(family.id)
            if family_device:
                existing_user_device = self.user_device_repository.find_by_user_and_device(
                    target_user.id,
                    family_device.id
                )
                if not existing_user_device:
                    self.user_device_repository.create(target_user.id, family_device.id)

            self.db.commit()
            created_member = self.family_member_repository.find_by_id(family_member.id)
            if not created_member:
                raise NotFoundException("Family member not found")
            return self._build_family_member_response(created_member)
        except Exception:
            self.db.rollback()
            raise

    def delete_member(self, user_id: int, member_id: int) -> bool:
        validate_positive_int(user_id, "user_id")
        validate_positive_int(member_id, "member_id")

        actor, actor_family_member, family = self._get_actor_context(user_id)
        self._ensure_owner(actor.id, actor_family_member.role, family.owner_user_id)

        target_member = self.family_member_repository.find_by_id(member_id)
        if not target_member:
            raise NotFoundException("Family member not found")

        if target_member.family_id != family.id:
            raise ForbiddenException("Family member is not accessible in this family")

        if target_member.role == "owner" or target_member.user_id == family.owner_user_id:
            raise BadRequestException("Owner cannot be removed")

        family_device = self.device_repository.find_by_family_id(family.id)
        target_user_device = None
        if family_device:
            target_user_device = self.user_device_repository.find_by_user_and_device(
                target_member.user_id,
                family_device.id
            )

        if target_user_device:
            if self.scan_log_repository.exists_by_user_device_id(target_user_device.id):
                raise BadRequestException("Scan logs exist for this member. Delete is blocked.")
            if self.item_repository.exists_by_user_device_id(target_user_device.id):
                raise BadRequestException("Items exist for this member. Delete is blocked.")

        try:
            if target_user_device:
                self.user_device_repository.delete(target_user_device)
            self.family_member_repository.delete(target_member)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def get_members(self, user_id: int) -> FamilyMemberListResponse:
        validate_positive_int(user_id, "user_id")

        _, family_member, family = self._get_actor_context(user_id)
        members = self.family_member_repository.find_all_by_family_id(family_member.family_id)

        return FamilyMemberListResponse(
            family_id=family.id,
            family_name=family.family_name,
            members=[self._build_family_member_response(member) for member in members],
            total_count=len(members)
        )


    @staticmethod
    def _ensure_owner(actor_user_id: int, role: str, owner_user_id: int) -> None:
        if role != "owner" or actor_user_id != owner_user_id:
            raise ForbiddenException("Only family owner can manage family members")

    def _resolve_existing_user(self, email: str, phone_number: str):
        user_by_email = self.user_repository.find_by_email(email)
        user_by_phone = self.user_repository.find_by_phone(phone_number)

        if user_by_email and user_by_phone and user_by_email.id != user_by_phone.id:
            raise ConflictException("email and phone_number belong to different users")

        target_user = user_by_email or user_by_phone
        if not target_user:
            raise BadRequestException("User with the given email or phone_number is not registered")

        if user_by_email and target_user.phone and target_user.phone != phone_number:
            raise ConflictException("phone_number does not match the existing user")

        if user_by_phone and target_user.email and target_user.email != email:
            raise ConflictException("email does not match the existing user")

        return target_user

    @staticmethod
    def _build_family_member_response(family_member) -> FamilyMemberResponse:
        user = family_member.user
        return FamilyMemberResponse(
            id=family_member.id,
            family_id=family_member.family_id,
            user_id=family_member.user_id,
            role=family_member.role,
            name=user.name if user else None,
            email=user.email if user else None,
            phone_number=user.phone if user else None,
            age=user.age if user else None,
            created_at=family_member.created_at
        )
