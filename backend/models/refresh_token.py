"""
JWT 리프레시 토큰 데이터베이스 모델

Smart Scan 시스템의 JWT 기반 인증에서 리프레시 토큰을 안전하게 관리하는 데이터베이스 모델입니다.
액세스 토큰의 재발급과 세션 관리를 위한 보안 강화된 토큰 저장소 역할을 수행합니다.

비즈니스 모델:
- 토큰 로테이션: 사용된 리프레시 토큰은 즉시 무효화하고 새 토큰 발급
- 보안 강화: 토큰 탈취 시 피해 최소화를 위한 만료 시간 관리
- 세션 추적: 사용자별 활성 세션 및 로그인 기기 관리

토큰 생명주기:
1. 발급 (created_at): 로그인 성공 시 새 리프레시 토큰 생성
2. 사용: 액세스 토큰 만료 시 리프레시 토큰으로 재발급
3. 로테이션: 사용된 토큰 무효화 및 새 토큰 발급
4. 만료/무효화: 시간 만료 또는 로그아웃 시 토큰 무효화

보안 기능:
- 고유 token_id를 통한 토큰 식별 및 중복 방지
- is_revoked 플래그로 즉시 토큰 무효화 가능
- 만료 시간 기반 자동 정리로 보안 위험 최소화
- 사용자별 토큰 추적으로 비정상 접근 감지

관계 연결:
- N:1 관계: user (토큰 소유자)
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from backend.common.db import Base


class RefreshToken(Base):
    """
    JWT 리프레시 토큰 모델

    사용자의 리프레시 토큰 정보를 저장하고 토큰 생명주기를 관리합니다.
    """
    __tablename__ = "refresh_tokens"

    # 기본 식별자
    id = Column(Integer, primary_key=True, index=True)  # 내부 토큰 레코드 ID

    # 사용자 연결
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # 토큰 소유자 사용자 ID

    # 토큰 정보
    token_id = Column(String(255), unique=True, nullable=False, index=True)  # 고유 토큰 식별자 (UUID)

    # 시간 관리
    created_at = Column(DateTime(timezone=True), nullable=False)  # 토큰 발급 시간
    expires_at = Column(DateTime(timezone=True), nullable=False)  # 토큰 만료 시간

    # 상태 관리
    is_revoked = Column(Boolean, default=False, nullable=False)  # 토큰 무효화 여부
    revoked_at = Column(DateTime(timezone=True), nullable=True)  # 토큰 무효화 시간

    # 관계 정의
    user = relationship("User")  # 토큰 소유자
