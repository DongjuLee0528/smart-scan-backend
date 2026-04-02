from sqlalchemy.orm import Session
from backend.models.device import Device
from typing import Optional


class DeviceRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_serial_number(self, serial_number: str) -> Optional[Device]:
        return self.db.query(Device).filter(Device.serial_number == serial_number).first()

    def find_by_id(self, device_id: int) -> Optional[Device]:
        return self.db.query(Device).filter(Device.id == device_id).first()

    def create(self, serial_number: str) -> Device:
        device = Device(serial_number=serial_number)
        self.db.add(device)
        self.db.flush()
        return device
