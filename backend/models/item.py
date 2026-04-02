from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.common.db import Base


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    user_device_id = Column(Integer, ForeignKey("user_devices.id"), nullable=False)
    tag_uid = Column(String(255), ForeignKey("master_tags.tag_uid"), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # relationships
    user_device = relationship("UserDevice", back_populates="items")
    master_tag = relationship("MasterTag", back_populates="items")
    scan_logs = relationship("ScanLog", back_populates="item")
