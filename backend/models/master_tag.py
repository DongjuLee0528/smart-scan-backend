from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from backend.common.db import Base


class MasterTag(Base):
    __tablename__ = "master_tags"

    id = Column(Integer, primary_key=True, index=True)
    tag_uid = Column(String(255), unique=True, nullable=False, index=True)
    label_id = Column(Integer, nullable=False, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)

    # relationships
    device = relationship("Device", back_populates="master_tags")
    items = relationship("Item", back_populates="master_tag")
