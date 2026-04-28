"""
RFID device database model

Database model for managing UHF RFID reader devices in Smart Scan system.
Stores registration, management, and family connection information for RFID readers connected to Raspberry Pi.

Business model:
- Device registration: Unique device identification based on serial number
- Family connection: Family-unit device ownership management
- Tag connection: Relationship with RFID tags registered to device

Device lifecycle:
1. Registration (created_at): Serial number registration of new device
2. Assignment (family_id): Grant device ownership to specific family
3. Usage: RFID tag scanning and item tracking
4. Release: Family connection release and reassignment waiting

Hardware configuration:
- Raspberry Pi + UHF RFID reader module
- Device identification through unique serial number
- Cloud communication through network connection

Relationship connections:
- N:1 relationship: family (family that owns the device)
- 1:N relationship: tags (tags registered to device)
- 1:N relationship: master_tags (master tags per device)
- 1:N relationship: user_devices (user device access permissions)
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.common.db import Base


class Device(Base):
    """
    RFID device model

    Stores and manages information for UHF RFID reader devices.
    """
    __tablename__ = "devices"

    # Basic identifier
    id = Column(Integer, primary_key=True, index=True)  # Internal device ID

    # Device information
    serial_number = Column(String(255), unique=True, nullable=False, index=True)  # RFID reader serial number (unique)

    # Connection information
    family_id = Column(Integer, ForeignKey("families.id"), nullable=True, index=True)  # Connected family ID (optional)

    # System information
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # Device registration time

    # Relationship definitions
    family = relationship("Family", back_populates="devices")  # Family that owns the device
    tags = relationship("Tag", back_populates="device")  # Tags registered to device
    user_devices = relationship("UserDevice", back_populates="device")  # User device access permissions
    master_tags = relationship("MasterTag", back_populates="device")  # Master tags per device
