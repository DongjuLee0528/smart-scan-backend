from typing import Optional

from sqlalchemy.orm import Session

from backend.common.exceptions import BadRequestException, ConflictException, ForbiddenException, NotFoundException
from backend.common.validator import validate_positive_int, validate_serial_number
from backend.repositories.device_repository import DeviceRepository
from backend.repositories.family_member_repository import FamilyMemberRepository
from backend.repositories.item_repository import ItemRepository
from backend.repositories.scan_log_repository import ScanLogRepository
from backend.repositories.user_device_repository import UserDeviceRepository
from backend.repositories.user_repository import UserRepository
from backend.schemas.device_schema import UserDeviceResponse


class DeviceService:
    """
    Smart Scan 디바이스 관리 서비스

    가족 단위로 사용하는 스캐너 디바이스의 등록, 연결, 해제를 담당한다.
    하나의 가족당 하나의 디바이스만 등록 가능하며, 가족 구성원 모두가 해당 디바이스를 공유한다.

    설계 의도:
    - 가족 공유 디바이스: 한 가족이 하나의 스캐너를 공동 사용하는 모델
    - 시리얼 번호 기반 등록: 물리적 디바이스와 1:1 매칭
    - 데이터 보호: 스캔 로그나 아이템이 존재하는 디바이스는 해제 불가
    - 자동 구성원 연결: 디바이스 등록 시 모든 가족 구성원에게 자동 연결
    """
    def __init__(self, db: Session):
        """디바이스 관리에 필요한 모든 리포지토리 초기화"""
        self.db = db
        self.user_repo = UserRepository(db)
        self.device_repo = DeviceRepository(db)
        self.family_member_repo = FamilyMemberRepository(db)
        self.user_device_repo = UserDeviceRepository(db)
        self.item_repo = ItemRepository(db)
        self.scan_log_repo = ScanLogRepository(db)

    def register_device(self, user_id: int, serial_number: str) -> UserDeviceResponse:
        """
        가족에 스캐너 디바이스 등록

        시리얼 번호로 디바이스를 찾아 요청자의 가족에 등록한다.
        등록 시 모든 가족 구성원이 자동으로 해당 디바이스에 연결되어 공동 사용이 가능해진다.
        가족당 하나의 디바이스만 등록 가능하며, 다른 가족에 이미 등록된 디바이스는 등록 불가하다.
        """
        validate_positive_int(user_id, "user_id")
        validate_serial_number(serial_number)

        # 사용자 정보 및 가족 소속 확인
        user, family_member = self._get_user_and_family_member(user_id)
        normalized_serial_number = serial_number.strip()

        # 시리얼 번호로 디바이스 존재 여부 확인
        device = self.device_repo.find_by_serial_number(normalized_serial_number)
        if not device:
            raise NotFoundException("Device not found")

        # 가족의 기존 디바이스 등록 상태 확인
        family_device = self.device_repo.find_by_family_id(family_member.family_id)
        if family_device and family_device.id != device.id:
            raise ConflictException("Family already has a registered device")

        # 타 가족에 이미 등록된 디바이스인지 확인
        if device.family_id is not None and device.family_id != family_member.family_id:
            raise ForbiddenException("Device is already registered to another family")

        try:
            # 디바이스를 가족에 할당 (미할당 상태인 경우만)
            if device.family_id is None:
                self.device_repo.assign_family(device, family_member.family_id)

            # 가족 구성원 전체에게 디바이스 연결 (중복 연결 방지)
            family_members = self.family_member_repo.find_all_by_family_id(family_member.family_id)
            for member in family_members:
                existing_user_device = self.user_device_repo.find_by_user_and_device(member.user_id, device.id)
                if existing_user_device:
                    continue
                self.user_device_repo.create(member.user_id, device.id)

            self.db.commit()
            user_device = self.user_device_repo.find_by_user_and_device(user.id, device.id)
            if not user_device:
                raise NotFoundException("Registered device link not found")
            return UserDeviceResponse.model_validate(user_device)
        except Exception:
            self.db.rollback()
            raise

    def get_my_device(self, user_id: int) -> Optional[UserDeviceResponse]:
        """
        내 가족의 등록된 디바이스 정보 조회

        사용자가 속한 가족에 등록된 디바이스가 있으면 해당 정보를 반환한다.
        가족에 등록된 디바이스가 없거나 사용자가 가족에 소속되지 않은 경우 None을 반환한다.
        """
        validate_positive_int(user_id, "user_id")

        # 사용자와 가족 정보 조회 (존재하지 않으면 None 반환)
        user, family_member = self._find_user_and_family_member(user_id)
        if not user or not family_member:
            return None

        # 가족에 등록된 디바이스 조회
        family_device = self.device_repo.find_by_family_id(family_member.family_id)
        if not family_device:
            return None

        # 사용자-디바이스 연결 정보 조회
        user_device = self.user_device_repo.find_by_user_and_device(user.id, family_device.id)
        if not user_device:
            return None

        return UserDeviceResponse.model_validate(user_device)

    def unlink_device(self, user_id: int) -> bool:
        """
        가족 디바이스 연결 해제

        가족에 등록된 디바이스를 완전히 해제한다.
        스캔 로그나 아이템이 존재하는 경우 데이터 보호를 위해 해제를 차단한다.
        해제 시 모든 가족 구성원의 연결이 함께 해제되고 디바이스는 미할당 상태가 된다.
        """
        validate_positive_int(user_id, "user_id")

        # 사용자의 가족 정보 및 등록된 디바이스 확인
        _, family_member = self._find_user_and_family_member(user_id)
        if not family_member:
            return False

        family_device = self.device_repo.find_by_family_id(family_member.family_id)
        if not family_device:
            return False

        # 모든 사용자-디바이스 연결 조회
        user_devices = self.user_device_repo.find_all_by_device_id(family_device.id)

        # 데이터 존재 여부 확인 (스캔 로그나 아이템이 있으면 해제 차단)
        for user_device in user_devices:
            if self.scan_log_repo.exists_by_user_device_id(user_device.id):
                raise BadRequestException("Scan logs exist for this device. Unlink is blocked.")

            if self.item_repo.exists_by_user_device_id(user_device.id):
                raise BadRequestException("Items exist for this device. Unlink is blocked.")

        try:
            # 모든 사용자-디바이스 연결 삭제 후 디바이스 가족 할당 해제
            self.user_device_repo.delete_many(user_devices)
            self.device_repo.clear_family(family_device)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def _get_user_and_family_member(self, user_id: int):
        """사용자와 가족 구성원 정보 조회 (필수 - 없으면 예외 발생)"""
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")

        family_member = self.family_member_repo.find_by_user_id(user.id)
        if not family_member:
            raise BadRequestException("User is not assigned to a family")

        return user, family_member

    def _find_user_and_family_member(self, user_id: int):
        """사용자와 가족 구성원 정보 조회 (선택적 - 없으면 None 반환)"""
        user = self.user_repo.find_by_id(user_id)
        if not user:
            return None, None

        # 가족 구성원 정보 조회 (없어도 사용자 정보는 반환)
        family_member = self.family_member_repo.find_by_user_id(user.id)
        if not family_member:
            return user, None

        return user, family_member
