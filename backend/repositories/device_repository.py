"""
RFID device data access layer

Repository responsible for database operations on UHF RFID reader devices.
Provides registration, lookup, and management functions for RFID readers connected to Raspberry Pi.

Data management:
- Device registration and serial number management
- Family-unit device connection status tracking
- Device metadata storage (registration date, status, etc.)

Business rules:
- Serial numbers must be unique throughout entire system
- One main device registration per family recommended
- Must check associated tag and item status when deleting devices

Main query patterns:
- Device lookup by serial number (used for device authentication)
- Family ID and device ID combination lookup (for permission verification)
- List all devices owned by family
"""

from typing import Optional

from sqlalchemy.orm import Session

from backend.models.device import Device


class DeviceRepository:
    """
    RFID device data access class

    Provides CRUD operations and business logic queries for device table.
    """
    def __init__(self, db: Session):
        """Inject database session"""
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
