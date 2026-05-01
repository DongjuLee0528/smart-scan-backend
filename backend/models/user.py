"""
User model

Database model for storing user information in SmartScan system.
Supports both KakaoTalk bot integration and web service users.
"""

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.common.db import Base


class User(Base):
    __tablename__ = "users"

    # Basic identifier
    id = Column(Integer, primary_key=True, index=True)  # Internal user ID

    # KakaoTalk integration info
    kakao_user_id = Column(String(255), unique=True, nullable=False, index=True)  # Kakao user unique ID

    # User basic information
    name = Column(String(255), nullable=True)  # User name
    email = Column(String(255), unique=True, nullable=True, index=True)  # Email address (for web login)
    password_hash = Column(String(255), nullable=True)  # Encrypted password (for web login)
    phone = Column(String(50), nullable=True)  # Phone number
    age = Column(Integer, nullable=True)  # Age

    # System information
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # Account creation time

    # relationships
    owned_families = relationship(
        "Family",
        back_populates="owner",
        foreign_keys="Family.owner_user_id"
    )
    owned_tags = relationship("Tag", back_populates="owner")
    family_members = relationship("FamilyMember", back_populates="user")
    user_devices = relationship("UserDevice", back_populates="user")
