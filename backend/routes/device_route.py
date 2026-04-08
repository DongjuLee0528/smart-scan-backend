from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from backend.common.dependencies import get_current_user
from backend.common.db import get_db
from backend.common.exceptions import BadRequestException
from backend.common.response import success_response
from backend.schemas.device_schema import DeviceRegisterRequest
from backend.services.device_service import DeviceService


router = APIRouter(tags=["devices"])


def get_device_service(db: Session = Depends(get_db)) -> DeviceService:
    return DeviceService(db)


@router.post("/register")
async def register_device(
    request: DeviceRegisterRequest,
    current_user=Depends(get_current_user),
    device_service: DeviceService = Depends(get_device_service)
):
    try:
        # 입력값 검증
        if not request.serial_number or not request.serial_number.strip():
            raise BadRequestException("serial_number는 필수입니다")

        user_device = device_service.register_device(current_user.id, request.serial_number)
        return success_response("Device registered successfully", user_device.model_dump())
    except ValidationError as e:
        raise BadRequestException(f"입력값 검증 실패: {str(e)}")
    except Exception as e:
        if isinstance(e, (BadRequestException, HTTPException)):
            raise
        raise HTTPException(status_code=500, detail="디바이스 등록 중 오류가 발생했습니다")


@router.get("/me")
async def get_my_device(
    current_user=Depends(get_current_user),
    device_service: DeviceService = Depends(get_device_service)
):
    try:
        user_device = device_service.get_my_device(current_user.id)

        if not user_device:
            return success_response("No device found", None)

        return success_response("Device found", user_device.model_dump())
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail="디바이스 조회 중 오류가 발생했습니다")


@router.delete("/me")
async def unlink_device(
    current_user=Depends(get_current_user),
    device_service: DeviceService = Depends(get_device_service)
):
    try:
        result = device_service.unlink_device(current_user.id)

        if result:
            return success_response("Device unlinked successfully")
        return success_response("No device to unlink")
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail="디바이스 해제 중 오류가 발생했습니다")
