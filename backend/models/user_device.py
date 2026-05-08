"""
User Device Association Model

Database model representing the many-to-many relationship between users and RFID devices.
Manages which users are authorized to use which devices within the Smart Scan system.

Business Rules:
- Users can be associated with multiple devices
- Devices can have multiple authorized users (family sharing)
- Association is tracked with creation timestamp
- Primary use case: Family members sharing RFID readers

Relationship Connections:
- N:1 relationship: user (User who can access the device)
- N:1 relationship: device (RFID device being accessed)
- 1:N relationship: items (Items registered through this user-device pair)
- 1:N relationship: scan_logs (Scan events from this user-device pair)
"""

from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.common.db import Base


class UserDevice(Base):
    """
    User-Device association model

    Links users to RFID devices they are authorized to use.
    Enables family sharing of devices and tracking of user-specific activities.
    """
    __tablename__ = "user_devices"

    # Primary identifier
    id = Column(Integer, primary_key=True, index=True)

    # Foreign key relationships
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # User authorized to use device
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)  # RFID device being accessed

    # Timestamp tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # When association was created

    # ORM relationships
    user = relationship("User", back_populates="user_devices")  # User who can access device
    device = relationship("Device", back_populates="user_devices")  # Device being accessed
    items = relationship("Item", back_populates="user_device")  # Items registered by this user-device pair
    scan_logs = relationship("ScanLog", back_populates="user_device")  # Scan activities from this user-device pair