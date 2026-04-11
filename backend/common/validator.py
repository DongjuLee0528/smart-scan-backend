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
