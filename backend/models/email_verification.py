"""
이메일 인증 데이터베이스 모델

Smart Scan 시스템의 회원가입 시 이메일 소유권 확인을 위한 인증 코드 관리 모델입니다.
6자리 숫자 인증 코드의 생성, 검증, 사용 상태를 추적하여 안전한 회원가입을 보장합니다.

비즈니스 모델:
- 인증 코드: 6자리 숫자로 구성된 일회용 코드
- 만료 시간: 설정 가능한 시간 후 자동 만료
- 검증 상태: 인증 완료와 사용 완료를 별도 관리
- 보안 강화: 중복 사용 방지 및 시간 기반 만료

데이터 생명주기:
1. 생성 (created_at): 사용자가 이메일 인증 요청
2. 검증 (verified_at): 사용자가 올바른 코드 입력
3. 사용 (used_at): 실제 회원가입 완료 시 코드 소모
4. 만료 (expires_at): 설정된 시간 후 자동 무효화

관계 연결:
- 독립적인 테이블 (외래키 관계 없음)
- 이메일 주소를 통한 사용자와 논리적 연결
"""

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func
from backend.common.db import Base


class EmailVerification(Base):
    """
    이메일 인증 모델

    회원가입 시 이메일 소유권 확인을 위한 인증 코드 정보를 저장하고 관리합니다.
    """
    __tablename__ = "email_verifications"

    # 기본 식별자
    id = Column(Integer, primary_key=True, index=True)  # 내부 인증 ID

    # 인증 대상 정보
    email = Column(String(255), nullable=False, index=True)  # 인증받을 이메일 주소
    code = Column(String(6), nullable=False)  # 6자리 숫자 인증 코드

    # 시간 관리
    expires_at = Column(DateTime(timezone=True), nullable=False)  # 인증 코드 만료 시간
    verified_at = Column(DateTime(timezone=True), nullable=True)  # 코드 검증 완료 시간
    used_at = Column(DateTime(timezone=True), nullable=True)  # 회원가입에 사용된 시간
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # 코드 생성 시간
