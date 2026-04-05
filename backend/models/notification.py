from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.common.db import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    sender_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    recipient_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(50), nullable=False)
    channel = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(String(1000), nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    family = relationship("Family")
    sender = relationship("User", foreign_keys=[sender_user_id])
    recipient = relationship("User", foreign_keys=[recipient_user_id])
