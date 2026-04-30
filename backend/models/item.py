"""
Item (personal belongings) model

Database model representing real objects connected to RFID tags.
Registered to track items that users carry when leaving through the door.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.common.db import Base


class Item(Base):
    __tablename__ = "items"

    # Basic identifier
    id = Column(Integer, primary_key=True, index=True)  # Internal item ID

    # Item basic information
    name = Column(String(255), nullable=False)  # Item name (e.g., "wallet", "phone")

    # Connection information
    user_device_id = Column(Integer, ForeignKey("user_devices.id"), nullable=False)  # Owner's device connection
    # When only name is added from chatbot, tag_uid is NULL (is_pending=True). Tag binding occurs when label is connected from web.
    tag_uid = Column(String(255), ForeignKey("master_tags.tag_uid"), nullable=True, index=True)

    # Status information
    is_active = Column(Boolean, default=True, nullable=False)  # Active status (excluded from scan when inactive)
    is_pending = Column(Boolean, default=False, nullable=False)  # Status waiting for label (tag_uid) connection after name-only addition from chatbot

    # System information
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # Item registration time
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )  # Last modification time

    # relationships
    user_device = relationship("UserDevice", back_populates="items")
    master_tag = relationship("MasterTag", back_populates="items")
    scan_logs = relationship("ScanLog", back_populates="item")
