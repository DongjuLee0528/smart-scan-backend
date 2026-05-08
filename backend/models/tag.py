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

    # Primary identifier
    id = Column(Integer, primary_key=True, index=True)  # Internal virtual tag ID

    # Tag information
    tag_uid = Column(String(255), unique=True, nullable=False, index=True)  # Unique tag identifier across system
    name = Column(String(255), nullable=False)  # User-defined tag name

    # Ownership and connection
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)  # Family this tag belongs to
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # User who owns this tag
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)  # Device this tag is registered to

    # Status information
    is_active = Column(Boolean, default=True, nullable=False)  # Whether tag is active or deactivated

    # Timestamp tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # When tag was created
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )  # Last modification time

    # ORM relationships
    family = relationship("Family", back_populates="tags")  # Family this tag belongs to
    owner = relationship("User", back_populates="owned_tags")  # User who owns this tag
    device = relationship("Device", back_populates="tags")  # Device this tag is registered to
