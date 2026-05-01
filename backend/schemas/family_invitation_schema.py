"""
Family invitation Pydantic schemas

Defines schemas for request/response serialization and input validation.

Provided schemas:
- CreateInvitationRequest: Invitation creation request body
- InvitationResponse: Single invitation response (minimized sensitive information)
- InvitationListResponse: Invitation list response
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


class CreateInvitationRequest(BaseModel):
    """
    Invitation creation request body

    Used when family owner invites new member via email.
    name, phone_number are reference information displayed in invitation email body
    and actual registration info is processed based on current_user upon acceptance.
    """
    name: str
    email: str
    phone_number: str
    age: Optional[int] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name is required")
        return v

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        v = v.strip()
        if not v or "@" not in v:
            raise ValueError("Email format is invalid")
        return v

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Phone number is required")
        return v

    @field_validator("age")
    @classmethod
    def validate_age(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 0 or v > 150):
            raise ValueError("Age must be between 0-150")
        return v


class InvitationResponse(BaseModel):
    """
    Single invitation response

    Uses same format for both by-token public query and owner list query.
    Minimizes sensitive information by exposing only recipient email and status, family/inviter names.
    """
    id: int
    family_id: int
    family_name: str
    inviter_name: str
    email: str
    status: str
    expires_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class InvitationListResponse(BaseModel):
    """
    Family pending invitation list response
    """
    invitations: list[InvitationResponse]
    total_count: int


class AcceptInvitationResponse(BaseModel):
    """
    Invitation acceptance success response - return moved family info
    """
    family_id: int
    family_name: str
    role: str


class DeclineInvitationResponse(BaseModel):
    """
    Invitation decline success response
    """
    status: str
