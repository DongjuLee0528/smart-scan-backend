import re
from backend.common.exceptions import BadRequestException


def validate_kakao_user_id(kakao_user_id: str) -> None:
    if not kakao_user_id or not isinstance(kakao_user_id, str):
        raise BadRequestException("kakao_user_id is required")

    if len(kakao_user_id.strip()) == 0:
        raise BadRequestException("kakao_user_id cannot be empty")


def validate_serial_number(serial_number: str) -> None:
    if not serial_number or not isinstance(serial_number, str):
        raise BadRequestException("serial_number is required")

    if len(serial_number.strip()) == 0:
        raise BadRequestException("serial_number cannot be empty")

    # 영숫자와 하이픈, 언더스코어만 허용
    if not re.match(r'^[a-zA-Z0-9_-]+$', serial_number):
        raise BadRequestException("serial_number contains invalid characters")


def validate_status(status: str, allowed_values: list) -> None:
    if not status or not isinstance(status, str):
        raise BadRequestException("status is required")

    if status not in allowed_values:
        raise BadRequestException(f"status must be one of: {', '.join(allowed_values)}")


def validate_positive_int(value: int, field_name: str) -> None:
    if not isinstance(value, int) or value <= 0:
        raise BadRequestException(f"{field_name} must be a positive integer")


def validate_non_empty_string(value: str, field_name: str) -> None:
    if not value or not isinstance(value, str) or len(value.strip()) == 0:
        raise BadRequestException(f"{field_name} is required and cannot be empty")
