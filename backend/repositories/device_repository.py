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
        Query device by serial number

        Identify device through serial number when RFID reader sends scan data.
        """
        return self.db.query(Device).filter(Device.serial_number == serial_number).first()

    def find_by_id(self, device_id: int) -> Optional[Device]:
        """
        Query by device ID

        Args:
            device_id: Unique ID of device to query

        Returns:
            Optional[Device]: Matching device or None
        """
        return self.db.query(Device).filter(Device.id == device_id).first()

    def find_by_id_and_family_id(self, device_id: int, family_id: int) -> Optional[Device]:
        """
        Query device by device ID and family ID (for permission verification)

        Used to verify if specific family has permission to access the device.

        Args:
            device_id: Unique ID of device to query
            family_id: Unique ID of family to verify permission

        Returns:
            Optional[Device]: Device owned by family or None
        """
        return self.db.query(Device).filter(
            Device.id == device_id,
            Device.family_id == family_id
        ).first()

    def find_by_family_id(self, family_id: int) -> Optional[Device]:
        """
        Query device registered by family ID

        Currently structured to register one main device per family.

        Args:
            family_id: Unique ID of family to query

        Returns:
            Optional[Device]: Device registered to family or None
        """
        return self.db.query(Device).filter(Device.family_id == family_id).first()

    def assign_family(self, device: Device, family_id: int) -> Device:
        """
        Assign device to family

        Args:
            device: Device entity to assign
            family_id: Unique ID of family to receive assignment

        Returns:
            Device: Updated device entity
        """
        device.family_id = family_id
        self.db.flush()
        return device

    def clear_family(self, device: Device) -> Device:
        """
        Clear device family assignment

        Args:
            device: Device entity to clear assignment

        Returns:
            Device: Updated device entity
        """
        device.family_id = None
        self.db.flush()
        return device

    def create(self, serial_number: str) -> Device:
        """
        Create new device

        Args:
            serial_number: Serial number of RFID reader

        Returns:
            Device: Created device entity
        """
        device = Device(serial_number=serial_number)
        self.db.add(device)
        self.db.flush()
        return device
