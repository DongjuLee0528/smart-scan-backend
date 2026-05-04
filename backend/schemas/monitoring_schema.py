"""
Monitoring Dashboard API Schema

Defines API schemas used in the Smart Scan system's monitoring dashboard.
Systematically manages tag status by family members, overall status, and individual tag tracking information.

Main Schemas:
- TagCurrentStatus: Current status of tags (registered, found, lost)
- MemberSummaryResponse: Summary of tag status by family member
- TagStatusResponse: Detailed status information of individual tags
- MonitoringDashboardResponse: Complete family monitoring dashboard
- MemberTagStatusListResponse: Tag list for specific member
- MyTagStatusListResponse: Personal tag list

Data Structure:
- Tag status: Track registered, found, lost status
- Ownership information: Manage tag owners and responsible persons
- Time tracking: Record last seen and scan times
- Statistics: Aggregate data by member and status

Business Rules:
- Family members can view each other's tag status
- Tag status updates in real-time
- Lost tags are linked with notification system
- Statistics data optimized with caching for performance

Usage Scenarios:
- View family-wide tag status dashboard
- Check specific member's belongings status
- Quick identification and notification of lost items
- Monitor family belongings management status
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class TagCurrentStatus(str, Enum):
    """
    Tag current status enumeration

    Represents the current tracking status of RFID tags.
    """
    REGISTERED = "REGISTERED"  # Registered - tag registered but not yet scanned
    FOUND = "FOUND"  # Found - tag recently scanned and location confirmed
    LOST = "LOST"  # Lost - tag not scanned for a certain period and considered lost


class MemberSummaryResponse(BaseModel):
    """
    Family member tag status summary response schema

    Used to display tag status statistics for each member on the dashboard.
    """
    member_id: int  # Family member ID
    user_id: int  # Connected user ID
    name: Optional[str] = None  # Member name
    email: Optional[str] = None  # Member email
    role: str  # Role within family (owner, member)
    tag_count: int  # Total number of tags
    found_count: int  # Number of found tags
    lost_count: int  # Number of lost tags
    registered_count: int  # Number of registered tags


class TagStatusResponse(BaseModel):
    """
    Individual tag status detailed response schema

    Includes tag's current status, owner, and connected item information.
    """
    tag_id: int  # Tag ID
    tag_uid: str  # RFID tag unique identifier
    name: str  # Tag name
    owner_user_id: int  # Tag owner user ID
    owner_member_id: Optional[int] = None  # Tag owner member ID
    owner_name: Optional[str] = None  # Tag owner name
    status: TagCurrentStatus  # Current tag status
    is_active: bool  # Tag active status
    item_id: Optional[int] = None  # Connected item ID
    item_name: Optional[str] = None  # Connected item name
    device_id: Optional[int] = None  # Last scanned device ID
    last_seen_at: Optional[datetime] = None  # Last seen time
    last_scanned_at: Optional[datetime] = None  # Last scanned time
    created_at: datetime  # Tag registration time
    updated_at: datetime  # Tag information update time


class DashboardSummaryResponse(BaseModel):
    """
    Dashboard overall summary response schema

    Provides summary information for viewing the entire family's tag status at a glance.
    """
    total_members: int  # Total number of family members
    total_tags: int  # Total number of registered tags
    found_count: int  # Number of found tags
    lost_count: int  # Number of lost tags
    registered_count: int  # Number of newly registered tags


class MonitoringDashboardResponse(BaseModel):
    """
    Main monitoring dashboard response schema

    Dashboard data that comprehensively provides monitoring status for the entire family.
    """
    family_id: int  # Family ID
    family_name: str  # Family name
    requester_member_id: int  # Requester member ID
    requester_role: str  # Requester role
    summary: DashboardSummaryResponse  # Overall summary information
    members: list[MemberSummaryResponse]  # Member summary information list


class MemberTagStatusListResponse(BaseModel):
    """
    Specific member's tag status list response schema

    Used when querying the status of all tags owned by a specific family member.
    """
    family_id: int  # Family ID
    family_name: str  # Family name
    member_id: int  # Target member ID for query
    user_id: int  # Target user ID for query
    member_name: Optional[str] = None  # Member name
    role: str  # Member role
    tags: list[TagStatusResponse]  # Tag status list
    total_count: int  # Total number of tags


class MyTagStatusListResponse(BaseModel):
    """
    Personal tag status list response schema

    Used when querying the logged-in user's own tag list.
    """
    family_id: int  # Family ID
    family_name: str  # Family name
    member_id: int  # Personal member ID
    tags: list[TagStatusResponse]  # Personal tag status list
    total_count: int  # Total number of tags
