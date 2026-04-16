"""
RFID 디바이스 데이터 접근 계층

UHF RFID 리더기 디바이스의 데이터베이스 작업을 담당하는 레포지토리입니다.
라즈베리파이에 연결된 RFID 리더기의 등록, 조회, 관리 기능을 제공합니다.

데이터 관리:
- 디바이스 등록 및 시리얼 번호 관리
- 가족 단위 디바이스 연결 상태 추적
- 디바이스 메타데이터 (등록일, 상태 등) 저장

비즈니스 규칙:
- 시리얼 번호는 전체 시스템에서 고유해야 함
- 한 가족당 하나의 주 디바이스 등록 권장
- 디바이스 삭제 시 연관된 태그와 아이템 상태 확인 필수

주요 쿼리 패턴:
- 시리얼 번호로 디바이스 조회 (디바이스 인증 시 사용)
- 가족 ID와 디바이스 ID 조합 조회 (권한 검증용)
- 가족이 소유한 모든 디바이스 목록 조회
"""

from typing import Optional

from sqlalchemy.orm import Session

from backend.models.device import Device


class DeviceRepository:
    """
    RFID 디바이스 데이터 접근 클래스

    디바이스 테이블에 대한 CRUD 작업과 비즈니스 로직 쿼리를 제공합니다.
    """
    def __init__(self, db: Session):
        """데이터베이스 세션 주입"""
        self.db = db

    def find_by_serial_number(self, serial_number: str) -> Optional[Device]:
        """
        시리얼 번호로 디바이스 조회

        RFID 리더기가 스캔 데이터를 전송할 때 시리얼 번호를 통해 디바이스를 식별합니다.
        """
        return self.db.query(Device).filter(Device.serial_number == serial_number).first()

    def find_by_id(self, device_id: int) -> Optional[Device]:
        """
        디바이스 ID로 조회

        Args:
            device_id: 조회할 디바이스의 고유 ID

        Returns:
            Optional[Device]: 일치하는 디바이스 또는 None
        """
        return self.db.query(Device).filter(Device.id == device_id).first()

    def find_by_id_and_family_id(self, device_id: int, family_id: int) -> Optional[Device]:
        """
        디바이스 ID와 가족 ID로 디바이스 조회 (권한 검증용)

        특정 가족이 해당 디바이스에 접근할 권한이 있는지 확인할 때 사용합니다.

        Args:
            device_id: 조회할 디바이스의 고유 ID
            family_id: 권한을 확인할 가족의 고유 ID

        Returns:
            Optional[Device]: 가족이 소유한 디바이스 또는 None
        """
        return self.db.query(Device).filter(
            Device.id == device_id,
            Device.family_id == family_id
        ).first()

    def find_by_family_id(self, family_id: int) -> Optional[Device]:
        """
        가족 ID로 등록된 디바이스 조회

        현재는 가족당 하나의 주 디바이스를 등록하는 구조입니다.

        Args:
            family_id: 조회할 가족의 고유 ID

        Returns:
            Optional[Device]: 가족에 등록된 디바이스 또는 None
        """
        return self.db.query(Device).filter(Device.family_id == family_id).first()

    def assign_family(self, device: Device, family_id: int) -> Device:
        """
        디바이스를 가족에 할당

        Args:
            device: 할당할 디바이스 엔티티
            family_id: 할당받을 가족의 고유 ID

        Returns:
            Device: 업데이트된 디바이스 엔티티
        """
        device.family_id = family_id
        self.db.flush()
        return device

    def clear_family(self, device: Device) -> Device:
        """
        디바이스 가족 할당 해제

        Args:
            device: 할당 해제할 디바이스 엔티티

        Returns:
            Device: 업데이트된 디바이스 엔티티
        """
        device.family_id = None
        self.db.flush()
        return device

    def create(self, serial_number: str) -> Device:
        """
        새 디바이스 생성

        Args:
            serial_number: RFID 리더기의 시리얼 번호

        Returns:
            Device: 생성된 디바이스 엔티티
        """
        device = Device(serial_number=serial_number)
        self.db.add(device)
        self.db.flush()
        return device
