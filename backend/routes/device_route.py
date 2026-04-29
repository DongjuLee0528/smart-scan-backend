"""
Device management API router

Provides API endpoints for UHF RFID reader device registration and management.
Registers RFID readers connected to Raspberry Pi to the system and connects them to users.

Main endpoints:
- POST /register: Register new device with device serial number
- GET /my-devices: Retrieve device list registered by current user
- DELETE /{device_id}: Unregister device

Security: JWT authentication required, users can only manage their own devices
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.common.dependencies import get_current_user
from backend.common.db import get_db
from backend.common.response import success_response
from backend.common.route_decorators import handle_service_errors, validate_required_string
from backend.schemas.device_schema import DeviceRegisterRequest
from backend.services.device_service import DeviceService


router = APIRouter(tags=["devices"])


def get_device_service(db: Session = Depends(get_db)) -> DeviceService:
    return DeviceService(db)


@router.post("/register")
@handle_service_errors
async def register_device(
    request: DeviceRegisterRequest,
    current_user=Depends(get_current_user),
    device_service: DeviceService = Depends(get_device_service)
):
    """
    Register RFID device

    Register new UHF RFID reader to system and connect with current user.
    Registration is processed through serial number of RFID reader connected to Raspberry Pi.

    Args:
        request: Registration request data containing device serial number
        current_user: Current authenticated user information (extracted from JWT token)

    Returns:
        Registered device information and user connection information

    Raises:
        ValidationError: When serial number is missing or invalid format
        ConflictError: When serial number is already registered
        AuthenticationError: When user is not authenticated
    """
    validate_required_string("serial_number", request.serial_number)

    user_device = device_service.register_device(current_user.id, request.serial_number)
    return success_response("Device registered successfully", user_device.model_dump())


@router.get("/me")
@handle_service_errors
async def get_my_device(
    current_user=Depends(get_current_user),
    device_service: DeviceService = Depends(get_device_service)
):
    user_device = device_service.get_my_device(current_user.id)

    if not user_device:
        return success_response("No device found", None)

    return success_response("Device found", user_device.model_dump())


@router.delete("/me")
@handle_service_errors
async def unlink_device(
    current_user=Depends(get_current_user),
    device_service: DeviceService = Depends(get_device_service)
):
    result = device_service.unlink_device(current_user.id)

    if result:
        return success_response("Device unlinked successfully")
    return success_response("No device to unlink")