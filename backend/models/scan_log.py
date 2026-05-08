"""
RFID scan log database model

Database model for recording all scan events from RFID readers.
Each scan event is recorded as FOUND or LOST status.

Data structure:
- Scan events: Records of moments when RFID reader detects tags
- Status tracking: Track current location of items with FOUND/LOST status
- Time-ordered data: Record door passage timing and sequence

Business logic:
- Door passage detection: Automatic scan whenever user passes through door
- Item tracking: Detect missing items by comparing LOST status after last FOUND status
- Notification trigger: Automatic notification when missing items are found
- Data analysis: Provide usage patterns and statistics by time period

Relationship connections:
- N:1 relationships: user_device, item
- Index: scanned_at (for time-ordered queries)
"""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.common.db import Base


class ScanLog(Base):
    """
    RFID scan log model

    Represents log data recording scan events from RFID readers.
    """
    __tablename__ = "scan_logs"

    # Primary identifier
    id = Column(Integer, primary_key=True, index=True)  # Internal scan log ID

    # Foreign key relationships
    user_device_id = Column(Integer, ForeignKey("user_devices.id"), nullable=False)  # User-device pair that performed scan
    item_id = Column(Integer, ForeignKey("items.id"), nullable=True)  # Item that was scanned (null for unregistered tags)

    # Scan information
    status = Column(String(50), nullable=False)  # Scan status: FOUND or LOST
    scanned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)  # When scan occurred

    # ORM relationships
    user_device = relationship("UserDevice", back_populates="scan_logs")  # User-device that performed scan
    item = relationship("Item", back_populates="scan_logs")  # Item that was scanned