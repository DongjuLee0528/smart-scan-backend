"""
Family group database model

Database model representing family groups, which are core concepts in SmartScan system.
Manages RFID devices and personal items shared at family level.

Business model:
- Family Owner: User who created the family group, has all management privileges
- Family Members: Users invited to family, with limited privileges
- Device Sharing: One RFID reader shared among one family
- Item Sharing: All family members can check each other's item status

Relationship connections:
- 1:N relationships: devices, tags, family_members
- N:1 relationship: owner (User)
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.common.db import Base


class Family(Base):
    """
    Family group model

    Represents groups that share and use RFID systems at family level.
    """
    __tablename__ = "families"

    id = Column(Integer, primary_key=True, index=True)
    family_name = Column(String(255), nullable=False)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # relationships
    devices = relationship("Device", back_populates="family")
    tags = relationship("Tag", back_populates="family")
    owner = relationship("User", back_populates="owned_families", foreign_keys=[owner_user_id])
    family_members = relationship("FamilyMember", back_populates="family")
