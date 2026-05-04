"""
Master tag database model

Database model representing actual physical RFID tags.
Represents actual tags connected to RFID readers, later connected to items.

Business model:
- Physical tags: Actually existing RFID tag hardware
- Device dependency: Tags attached to specific RFID reader devices
- Label system: Category classification support through label_id
- Item connection waiting: Tags not yet connected to items

Data integrity:
- tag_uid uniqueness: Unique identifier throughout entire system
- Device connection: Tags connected only to specific RFID readers
- Label-based classification: Used for tag grouping in business logic

Relationship connections:
- N:1 relationship: device
- 1:N relationship: items (multiple items can connect per tag)
"""

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from backend.common.db import Base


class MasterTag(Base):
    """
    Master tag model

    Data model representing actual physical RFID tag hardware.
    """
    __tablename__ = "master_tags"

    # Primary identifier
    id = Column(Integer, primary_key=True, index=True)  # Internal master tag ID

    # Tag information
    tag_uid = Column(String(255), unique=True, nullable=False, index=True)  # Unique RFID tag identifier
    label_id = Column(Integer, nullable=False, index=True)  # Label number for categorization (e.g., 1, 2, 3...)

    # Device connection
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)  # RFID device this tag is registered to

    # ORM relationships
    device = relationship("Device", back_populates="master_tags")  # RFID device this tag belongs to
    items = relationship("Item", back_populates="master_tag")  # Items connected to this master tag
