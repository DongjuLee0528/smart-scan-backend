"""
Virtual tag database model

Database model representing virtual tags created by users.
Manages logical tag information before being connected to actual physical RFID tags.

Business model:
- Virtual tags: Logical tags created by users on web
- Physical connection: Later mapped to actual RFID tags via tag_uid
- User ownership: Each tag is owned by specific user
- Family sharing: Family members can view each other's tags

Data attributes:
- tag_uid: Unique identifier throughout entire system
- Live item connection: Supports state not yet connected to items
- Deactivation: Hide unused tags by deactivating them

Relationship connections:
- N:1 relationships: family, owner_user
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.common.db import Base


class Tag(Base):
    """
    Virtual tag model

    Logical model representing virtual tag information created by users.
    """
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    tag_uid = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # relationships
    family = relationship("Family", back_populates="tags")
    owner = relationship("User", back_populates="owned_tags")
    device = relationship("Device", back_populates="tags")
