"""
API 응답 표준화 모듈

SmartScan 백엔드 API의 통일된 응답 형식을 제공하는 모듈입니다.
모든 API 엔드포인트에서 일관된 응답 구조를 사용하여 클라이언트의 응답 처리를 단순화합니다.

응답 형식:
- success: 요청 성공 여부 (boolean)
- message: 사용자에게 표시할 메시지 (string)
- data: 실제 응답 데이터 (선택적, Any 타입)

사용 예:
- success_response("데이터 조회 완료", user_data)
- error_response("사용자를 찾을 수 없습니다", 404)
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