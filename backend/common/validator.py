"""
Input data validation module

Module responsible for validating all input data in the SmartScan system.
Validates format, length, range of user inputs to ensure data integrity.

Validation features:
- Kakao user ID format validation
- Device serial number validation
- Email format and domain validation
- Tag UID format validation
- Numeric range validation (positive numbers, ID values, etc.)
- String length and required value validation

Exception handling: Raises BadRequestException for all validation failures
"""

import re

from backend.common.exceptions import BadRequestException


def validate_kakao_user_id(kakao_user_id: str) -> None:
    """
    Validate Kakao user ID

    Validates the validity of unique user ID provided by KakaoTalk platform.
    Rejects empty values, None, and strings with only whitespace.

    Args:
        kakao_user_id: Kakao user ID to validate

    Raises:
        BadRequestException: When ID is missing or empty string
    """
    if not kakao_user_id or not isinstance(kakao_user_id, str):
        raise BadRequestException("kakao_user_id is required")

    if len(kakao_user_id.strip()) == 0:
        raise BadRequestException("kakao_user_id cannot be empty")


def validate_serial_number(serial_number: str) -> None:
    """
    Validate RFID device serial number

    Validates serial number format of UHF RFID readers.
    Only allows alphanumeric characters, hyphens, underscores to block security-risky characters.

    Args:
        serial_number: Serial number to validate

    Raises:
        BadRequestException: When serial number is missing or invalid format

    Allowed characters: a-z, A-Z, 0-9, -, _
    """
    if not serial_number or not isinstance(serial_number, str):
        raise BadRequestException("serial_number is required")

    if len(serial_number.strip()) == 0:
        raise BadRequestException("serial_number cannot be empty")

    # Only allow alphanumeric characters, hyphens, and underscores
    if not re.match(r'^[a-zA-Z0-9_-]+$', serial_number):
        raise BadRequestException("serial_number contains invalid characters")


def validate_status(status: str, allowed_values: list) -> None:
    """
    Validate status value

    Checks if entered status is valid by comparing with allowed status value list.
    Used for scan log status, device status, etc.

    Args:
        status: Status value to validate
        allowed_values: List of allowed status values

    Raises:
        BadRequestException: When status is missing or not an allowed value

    Example:
        validate_status('FOUND', ['FOUND', 'LOST'])  # OK
        validate_status('INVALID', ['FOUND', 'LOST'])  # Exception
    """
    if not status or not isinstance(status, str):
        raise BadRequestException("status is required")

    if status not in allowed_values:
        raise BadRequestException(f"status must be one of: {', '.join(allowed_values)}")


def validate_positive_int(value: int, field_name: str) -> None:
    """
    Validate that value is a positive integer

    Args:
        value: Integer value to validate
        field_name: Name of the field for error messages

    Raises:
        BadRequestException: When value is not a positive integer
    """
    if not isinstance(value, int) or value <= 0:
        raise BadRequestException(f"{field_name} must be a positive integer")


def validate_non_empty_string(value: str, field_name: str) -> None:
    """
    Validate that string is not empty or whitespace-only

    Args:
        value: String value to validate
        field_name: Name of the field for error messages

    Raises:
        BadRequestException: When string is empty, None, or whitespace-only
    """
    if not value or not isinstance(value, str) or len(value.strip()) == 0:
        raise BadRequestException(f"{field_name} is required and cannot be empty")


def validate_email(email: str) -> None:
    """
    Validate email address format

    Uses basic regex to check for valid email format (user@domain.tld).
    Does not verify if email actually exists.

    Args:
        email: Email address to validate

    Raises:
        BadRequestException: When email is missing or has invalid format
    """
    if not email or not isinstance(email, str):
        raise BadRequestException("email is required")

    normalized_email = email.strip()
    if not normalized_email:
        raise BadRequestException("email cannot be empty")

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", normalized_email):
        raise BadRequestException("email format is invalid")


def validate_verification_code(code: str) -> None:
    """
    Validate 6-digit verification code

    Used for email verification codes and other numeric verification systems.

    Args:
        code: Verification code to validate

    Raises:
        BadRequestException: When code is missing or not exactly 6 digits
    """
    if not code or not isinstance(code, str):
        raise BadRequestException("code is required")

    normalized_code = code.strip()
    if not re.match(r"^\d{6}$", normalized_code):
        raise BadRequestException("code must be 6 digits")


def validate_optional_age(age: int | None) -> None:
    """
    Validate age value if provided

    Age is optional but if provided must be reasonable (1-150).

    Args:
        age: Age value to validate (can be None)

    Raises:
        BadRequestException: When age is invalid range
    """
    if age is None:
        return

    if not isinstance(age, int) or age <= 0 or age > 150:
        raise BadRequestException("age must be an integer between 1 and 150")


def validate_password(password: str) -> None:
    """
    Validate password complexity

    Enforces strong password policy:
    - Minimum 8 characters
    - Must contain letters, numbers, and special characters

    Args:
        password: Password to validate

    Raises:
        BadRequestException: When password doesn't meet complexity requirements
    """
    if not password or not isinstance(password, str):
        raise BadRequestException("password is required")

    normalized_password = password.strip()
    if len(normalized_password) < 8:
        raise BadRequestException("Password must be at least 8 characters and contain letters, numbers, and special characters")

    # Check for alphabetic characters
    if not re.search(r'[a-zA-Z]', normalized_password):
        raise BadRequestException("Password must be at least 8 characters and contain letters, numbers, and special characters")

    # Check for numeric characters
    if not re.search(r'[0-9]', normalized_password):
        raise BadRequestException("Password must be at least 8 characters and contain letters, numbers, and special characters")

    # Check for special characters
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', normalized_password):
        raise BadRequestException("Password must be at least 8 characters and contain letters, numbers, and special characters")
