"""
Notification database model

Database model for managing notifications between family members in Smart Scan system.
Systematically manages various notifications including departure/return status changes, system events, and emergency situations.

Business model:
- Sender-Recipient: Notification transmission between family members
- Notification types: Departure, return, emergency, system notifications, etc.
- Transmission channels: Email, SMS, push notifications, KakaoTalk, etc.
- Read status: Track whether recipient has checked notifications

Notification categories:
- Departure notifications: Notice when family members start going out
- Return notifications: Notice of return within expected time or delay
- Emergency notifications: Abnormal situations or security threats
- System notifications: Device status, battery, connection issues

Data flow:
1. Event detection (RFID scan, timeout, etc.)
2. Notification creation (determine sender, recipient, content)
3. Channel-specific transmission (email, SMS, etc.)
4. Read confirmation (status update based on user actions)

Relationship connections:
- N:1 relationships: family, sender, recipient (User)
- Family-unit notification management and member communication
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.common.db import Base


class Notification(Base):
    """
    Notification model

    Stores and manages various notification information between family members.
    """
    __tablename__ = "notifications"

    # Basic identifier
    id = Column(Integer, primary_key=True, index=True)  # Internal notification ID

    # Relationship information
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)  # Family ID where notification occurred
    sender_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # Notification sender user ID
    recipient_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # Notification recipient user ID

    # Notification metadata
    type = Column(String(50), nullable=False)  # Notification type (outbound, return, emergency, system)
    channel = Column(String(50), nullable=False)  # Notification channel (email, sms, push, kakao)
    title = Column(String(255), nullable=False)  # Notification title
    message = Column(String(1000), nullable=False)  # Notification content message

    # Status information
    is_read = Column(Boolean, default=False, nullable=False)  # Whether recipient has read
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # Notification creation time

    family = relationship("Family")
    sender = relationship("User", foreign_keys=[sender_user_id])
    recipient = relationship("User", foreign_keys=[recipient_user_id])
