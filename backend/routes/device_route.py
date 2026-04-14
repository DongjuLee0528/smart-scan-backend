"""
디바이스 관리 API 라우터

UHF RFID 리더 디바이스의 등록과 관리를 위한 API 엔드포인트를 제공합니다.
라즈베리파이에 연결된 RFID 리더기를 시스템에 등록하고 사용자와 연결합니다.

주요 엔드포인트:
- POST /register: 디바이스 시리얼 번호로 새 디바이스 등록
- GET /my-devices: 현재 사용자가 등록한 디바이스 목록 조회
- DELETE /{device_id}: 디바이스 등록 해제

보안: JWT 인증이 필요하며, 사용자는 본인의 디바이스만 관리 가능
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
    RFID 디바이스 등록

    새로운 UHF RFID 리더기를 시스템에 등록하고 현재 사용자와 연결합니다.
    라즈베리파이에 연결된 RFID 리더기의 시리얼 번호를 통해 등록 처리됩니다.

    Args:
        request: 디바이스 시리얼 번호가 포함된 등록 요청 데이터
        current_user: 현재 인증된 사용자 정보 (JWT 토큰에서 추출)

    Returns:
        등록된 디바이스 정보와 사용자 연결 정보

    Raises:
        ValidationError: 시리얼 번호가 없거나 형식이 잘못된 경우
        ConflictError: 이미 등록된 시리얼 번호인 경우
        AuthenticationError: 인증되지 않은 사용자인 경우
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