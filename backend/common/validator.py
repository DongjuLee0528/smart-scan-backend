"""
입력 데이터 검증 모듈

SmartScan 시스템의 모든 입력 데이터 검증을 담당하는 모듈입니다.
사용자 입력값의 형식, 길이, 범위 등을 검증하여 데이터 무결성을 보장합니다.

검증 기능:
- 카카오 사용자 ID 형식 검증
- 디바이스 시리얼 번호 검증
- 이메일 형식 및 도메인 검증
- 태그 UID 형식 검증
- 숫자 범위 검증 (양수, ID 값 등)
- 문자열 길이 및 필수 값 검증

예외 처리: 모든 검증 실패 시 BadRequestException 발생
"""

import re

from backend.common.exceptions import BadRequestException


def validate_kakao_user_id(kakao_user_id: str) -> None:
    """
    카카오 사용자 ID 검증

    카카오톡 플랫폼에서 제공하는 사용자 고유 ID의 유효성을 검증합니다.
    빈 값, None, 공백만 있는 문자열을 거부합니다.

    Args:
        kakao_user_id: 검증할 카카오 사용자 ID

    Raises:
        BadRequestException: ID가 없거나 빈 문자열인 경우
    """
    if not kakao_user_id or not isinstance(kakao_user_id, str):
        raise BadRequestException("kakao_user_id is required")

    if len(kakao_user_id.strip()) == 0:
        raise BadRequestException("kakao_user_id cannot be empty")


def validate_serial_number(serial_number: str) -> None:
    """
    RFID 디바이스 시리얼 번호 검증

    UHF RFID 리더기의 시리얼 번호 형식을 검증합니다.
    영숫자, 하이픈, 언더스코어만 허용하여 보안상 위험한 문자를 차단합니다.

    Args:
        serial_number: 검증할 시리얼 번호

    Raises:
        BadRequestException: 시리얼 번호가 없거나 잘못된 형식인 경우

    허용 문자: a-z, A-Z, 0-9, -, _
    """
    if not serial_number or not isinstance(serial_number, str):
        raise BadRequestException("serial_number is required")

    if len(serial_number.strip()) == 0:
        raise BadRequestException("serial_number cannot be empty")

    # 영숫자와 하이픈, 언더스코어만 허용
    if not re.match(r'^[a-zA-Z0-9_-]+$', serial_number):
        raise BadRequestException("serial_number contains invalid characters")


def validate_status(status: str, allowed_values: list) -> None:
    """
    상태 값 검증

    허용된 상태 값 목록과 대조하여 입력된 상태가 유효한지 확인합니다.
    스캔 로그 상태, 디바이스 상태 등에 사용됩니다.

    Args:
        status: 검증할 상태 값
        allowed_values: 허용된 상태 값 목록

    Raises:
        BadRequestException: 상태가 없거나 허용되지 않은 값인 경우

    Example:
        validate_status('FOUND', ['FOUND', 'LOST'])  # OK
        validate_status('INVALID', ['FOUND', 'LOST'])  # Exception
    """
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


def validate_email(email: str) -> None:
    if not email or not isinstance(email, str):
        raise BadRequestException("email is required")

    normalized_email = email.strip()
    if not normalized_email:
        raise BadRequestException("email cannot be empty")

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", normalized_email):
        raise BadRequestException("email format is invalid")


def validate_verification_code(code: str) -> None:
    if not code or not isinstance(code, str):
        raise BadRequestException("code is required")

    normalized_code = code.strip()
    if not re.match(r"^\d{6}$", normalized_code):
        raise BadRequestException("code must be 6 digits")


def validate_optional_age(age: int | None) -> None:
    if age is None:
        return

    if not isinstance(age, int) or age <= 0 or age > 150:
        raise BadRequestException("age must be an integer between 1 and 150")


def validate_password(password: str) -> None:
    if not password or not isinstance(password, str):
        raise BadRequestException("password is required")

    normalized_password = password.strip()
    if len(normalized_password) < 8:
        raise BadRequestException("비밀번호는 8자 이상이며 영문, 숫자, 특수문자를 포함해야 합니다")

    # 영문자 포함 확인
    if not re.search(r'[a-zA-Z]', normalized_password):
        raise BadRequestException("비밀번호는 8자 이상이며 영문, 숫자, 특수문자를 포함해야 합니다")

    # 숫자 포함 확인
    if not re.search(r'[0-9]', normalized_password):
        raise BadRequestException("비밀번호는 8자 이상이며 영문, 숫자, 특수문자를 포함해야 합니다")

    # 특수문자 포함 확인
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', normalized_password):
        raise BadRequestException("비밀번호는 8자 이상이며 영문, 숫자, 특수문자를 포함해야 합니다")
