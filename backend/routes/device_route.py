from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.common.db import get_db
from backend.common.response import success_response
from backend.schemas.device_schema import DeviceRegisterRequest, DeviceUnlinkRequest
from backend.services.device_service import DeviceService


router = APIRouter(tags=["devices"])


@router.post("/register")
async def register_device(
    request: DeviceRegisterRequest,
    db: Session = Depends(get_db)
):
    device_service = DeviceService(db)
    user_device = device_service.register_device(request.kakao_user_id, request.serial_number)
    return success_response("Device registered successfully", user_device.model_dump())


@router.get("/me")
async def get_my_device(
    kakao_user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    device_service = DeviceService(db)
    user_device = device_service.get_my_device(kakao_user_id)

    if not user_device:
        return success_response("No device found", None)

    return success_response("Device found", user_device.model_dump())


@router.delete("/me")
async def unlink_device(
    request: DeviceUnlinkRequest,
    db: Session = Depends(get_db)
):
    device_service = DeviceService(db)
    result = device_service.unlink_device(request.kakao_user_id)

    if result:
        return success_response("Device unlinked successfully")
    else:
        return success_response("No device to unlink")
