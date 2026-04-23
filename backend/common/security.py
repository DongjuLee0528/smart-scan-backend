"""
보안 관련 유틸리티 모듈

SmartScan 시스템의 인증, 비밀번호 해싱, JWT 토큰 관리 등 보안 기능을 담당하는 모듈입니다.
PBKDF2 기반 비밀번호 해싱과 JWT 액세스/리프레시 토큰 시스템을 구현합니다.

보안 기능:
- PBKDF2 + Salt를 이용한 안전한 비밀번호 해싱
- JWT 액세스 토큰 (15분 만료)과 리프레시 토큰 (30일 만료) 발급
- 토큰 검증 및 페이로드 추출
- HMAC 기반 보안 해시 생성

보안 정책:
- 비밀번호: PBKDF2-HMAC-SHA256, 100,000회 반복, 16바이트 솔트
- JWT: HS256 알고리즘, 동적 만료 시간 설정
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from jwt import InvalidTokenError

from backend.common.config import settings
from backend.common.exceptions import UnauthorizedException


def hash_password(password: str) -> str:
    """
    비밀번호 해싱 (PBKDF2-HMAC-SHA256)

    안전한 비밀번호 저장을 위해 PBKDF2 알고리즘과 무작위 솔트를 사용하여 해시를 생성합니다.
    Rainbow table 공격과 브루트 포스 공격에 대한 보안을 강화합니다.

    Args:
        password: 평문 비밀번호

    Returns:
        형식화된 해시 문자열 (pbkdf2_sha256$iterations$salt$hash)

    Security:
        - PBKDF2-HMAC-SHA256 알고리즘 사용
        - 100,000회 반복 (settings.PASSWORD_HASH_ITERATIONS)
        - 16바이트 랜덤 솔트 생성
    """
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        settings.PASSWORD_HASH_ITERATIONS
    )
    return (
        f"pbkdf2_sha256${settings.PASSWORD_HASH_ITERATIONS}$"
        f"{salt.hex()}${digest.hex()}"
    )


def verify_password(password: str, password_hash: str | None) -> bool:
    """
    비밀번호 검증

    사용자가 입력한 평문 비밀번호와 저장된 해시를 비교하여 일치하는지 확인합니다.
    타이밍 어택을 방지하기 위해 hmac.compare_digest를 사용합니다.

    Args:
        password: 사용자가 입력한 평문 비밀번호
        password_hash: 데이터베이스에 저장된 해시 (None 허용)

    Returns:
        비밀번호 일치 여부 (bool)

    Security:
        - hmac.compare_digest로 타이밍 어택 방지
        - 잘못된 형식의 해시는 False 반환
        - None 해시는 안전하게 False 처리
    """
    if not password_hash:
        return False

    try:
        algorithm, iterations, salt_hex, digest_hex = password_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    calculated_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        int(iterations)
    ).hex()
    return hmac.compare_digest(calculated_digest, digest_hex)


def generate_token_id() -> str:
    return uuid4().hex


def create_access_token(user_id: int) -> tuple[str, datetime]:
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp())
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expires_at


def create_refresh_token(user_id: int, token_id: str) -> tuple[str, datetime]:
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": token_id,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp())
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expires_at


def decode_token(token: str, expected_type: str | None = None) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        if expected_type and payload.get("type") != expected_type:
            raise UnauthorizedException("Invalid token type")

        return payload

    except InvalidTokenError as exc:
        raise UnauthorizedException("Invalid or expired token") from exc


def create_kakao_link_token(kakao_user_id: str) -> tuple[str, datetime]:
    """
    카카오 계정 연동용 단기 JWT 발급

    챗봇 Lambda 에서 미연동 사용자에게 전달할 링크에 포함되는 토큰.
    웹에서 사용자가 로그인 상태로 이 토큰을 제출하면 해당 kakao_user_id 를
    현재 로그인 사용자의 계정에 연결한다.

    JWT_SECRET_KEY 와 분리된 KAKAO_LINK_JWT_SECRET 으로 서명하여
    한쪽이 유출되어도 다른 쪽 토큰 체계가 위험해지지 않도록 격리한다.
    """
    if not kakao_user_id or not kakao_user_id.strip():
        raise ValueError("kakao_user_id is required")

    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(minutes=settings.KAKAO_LINK_TOKEN_EXPIRE_MINUTES)
    payload = {
        "kakao_user_id": kakao_user_id.strip(),
        "type": "kakao_link",
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(
        payload,
        settings.KAKAO_LINK_JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return token, expires_at


def decode_kakao_link_token(token: str) -> dict:
    """
    카카오 계정 연동 JWT 검증 및 페이로드 반환

    KAKAO_LINK_JWT_SECRET 로 서명 검증, type=="kakao_link" 여부와 만료 확인.
    반환 페이로드는 {"kakao_user_id", "type", "iat", "exp"} 구조.
    """
    try:
        payload = jwt.decode(
            token,
            settings.KAKAO_LINK_JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except InvalidTokenError as exc:
        raise UnauthorizedException("Invalid or expired kakao link token") from exc

    if payload.get("type") != "kakao_link":
        raise UnauthorizedException("Invalid token type")

    kakao_user_id = payload.get("kakao_user_id")
    if not kakao_user_id or not isinstance(kakao_user_id, str):
        raise UnauthorizedException("Invalid kakao link token payload")

    return payload
