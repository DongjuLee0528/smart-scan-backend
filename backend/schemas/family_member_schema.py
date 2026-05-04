"""
Family Member Management API Schema

Defines API schemas for adding, retrieving, and managing family members in the Smart Scan system.
Supports functionality for family owners to invite and manage new members.

Main Schemas:
- AddFamilyMemberRequest: Request to invite new family member
- FamilyMemberResponse: Family member detailed information response
- FamilyMemberListResponse: Family member list and family information response

Data Structure:
- Basic information: name, email, phone number, age (optional)
- Family role: owner, member
- Connection information: user account mapping

Business Rules:
- Only family owners can invite new members
- Invited members must create separate accounts and connect
- Member information is shared only within the family
- Optional information provision for privacy protection

Usage Scenarios:
- Family owners invite spouses or children to the system
- View family member list and manage contacts
- Manage member roles and permissions
- Set up family-wide item sharing
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


def _validate_required_text(value: str, field_name: str) -> str:
    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{field_name} is required")
    return normalized_value


class AddFamilyMemberRequest(BaseModel):
    name: str
    email: str
    phone_number: str
    age: Optional[int] = None

    @field_validator("name", "email", "phone_number")
    @classmethod
    def validate_required_text(cls, v: str, info) -> str:
        return _validate_required_text(v, info.field_name)


class FamilyMemberResponse(BaseModel):
    id: int
    family_id: int
    user_id: int
    role: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    age: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FamilyMemberListResponse(BaseModel):
    family_id: int
    family_name: str
    members: list[FamilyMemberResponse]
    total_count: int
