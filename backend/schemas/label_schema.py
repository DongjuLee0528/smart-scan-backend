"""
Label management API schema

Defines API schemas for label management features in Smart Scan system.
Supports querying and managing label numbers that can be assigned to RFID tags or items.

Main schemas:
- AvailableLabelResponse: Available label number list response

Data structure:
- Label number: Integer label identifier
- Availability info: Currently unassigned label numbers

Business rules:
- Label numbers cannot be duplicately assigned
- Labels in use are excluded from available list
- When label is released, included back in available list

Usage scenarios:
- Query available label numbers when registering new RFID tag
- Check empty label numbers when reassigning items
- System administrator's label status overview
"""

from pydantic import BaseModel
from typing import List


class AvailableLabelResponse(BaseModel):
    """
    Available label number response schema

    Returns list of currently unassigned label numbers.
    """
    available_labels: List[int]  # List of available label numbers