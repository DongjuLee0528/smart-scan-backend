"""
API response standardization module

Module that provides unified response format for SmartScan backend API.
Simplifies client response handling by using consistent response structure across all API endpoints.

Response format:
- success: Request success status (boolean)
- message: Message to display to user (string)
- data: Actual response data (optional, Any type)

Usage examples:
- success_response("Data retrieval completed", user_data)
- error_response("User not found", 404)
"""

from typing import Any, Optional, Dict
from pydantic import BaseModel


class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None


def success_response(message: str = "Success", data: Any = None) -> Dict[str, Any]:
    return {
        "success": True,
        "message": message,
        "data": data
    }


def error_response(message: str = "Error", data: Any = None) -> Dict[str, Any]:
    return {
        "success": False,
        "message": message,
        "data": data
    }