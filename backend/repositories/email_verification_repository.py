"""
이메일 인증 데이터 접근 계층

Smart Scan 시스템의 이메일 인증 프로세스를 위한 데이터베이스 접근 계층입니다.
6자리 인증 코드의 생성, 검증, 사용 과정을 안전하게 관리하여 스팸 방지와 보안을 강화합니다.

주요 기능:
- 이메일별 인증 코드 생성 및 관리
- 기존 미사용 코드 무효화 (보안 강화)
- 코드 검증 및 사용 상태 추적
- 만료 시간 기반 자동 정리

비즈니스 규칙:
- 이메일당 하나의 유효한 인증 코드만 존재
- 인증 완료와 사용 완료를 별도 추적
- 시간 기반 만료로 보안 위험 최소화
- 최신 코드 우선 조회로 일관성 보장

데이터 흐름:
1. 인증 요청 시 기존 미완료 코드 무효화
2. 새 인증 코드 생성 및 발송
3. 사용자 코드 입력 시 검증 수행
4. 회원가입 완료 시 코드 사용 처리

보안 강화:
- 동시성 제어를 통한 중복 코드 방지
- 만료된 코드 자동 무효화
- 사용된 코드 재사용 방지
"""

from datetime import datetime
from sqlalchemy.orm import Session
from backend.models.email_verification import EmailVerification


class EmailVerificationRepository:
    """
    이메일 인증 데이터 접근 클래스

    이메일 인증 코드의 전체 생명주기를 관리하는 데이터베이스 접근 계층입니다.
    """
    def __init__(self, db: Session):
        """데이터베이스 세션 주입"""
        self.db = db

    def invalidate_pending_by_email(self, email: str, now: datetime) -> None:
        """
        지정 이메일의 미완료 인증 코드 모두 무효화

        새로운 인증 코드 발송 전에 기존 미사용 코드들을 모두 만료시켜
        보안을 강화하고 중복 코드 발송을 방지합니다.

        Args:
            email: 인증 코드를 무효화할 이메일 주소
            now: 현재 시간 (UTC)

        무효화 대상:
            - 검증되지 않음 (verified_at IS NULL)
            - 사용되지 않음 (used_at IS NULL)
            - 아직 만료되지 않음 (expires_at > now)
        """
        self.db.query(EmailVerification).filter(
            EmailVerification.email == email,
            EmailVerification.verified_at.is_(None),
            EmailVerification.used_at.is_(None),
            EmailVerification.expires_at > now
        ).update(
            {EmailVerification.expires_at: now},
            synchronize_session=False
        )

    def create(self, email: str, code: str, expires_at: datetime) -> EmailVerification:
        """
        새로운 이메일 인증 코드 생성

        Args:
            email: 인증 대상 이메일 주소
            code: 6자리 숫자 인증 코드
            expires_at: 코드 만료 시간 (UTC)

        Returns:
            EmailVerification: 생성된 인증 코드 엔티티
        """
        verification = EmailVerification(
            email=email,
            code=code,
            expires_at=expires_at
        )
        self.db.add(verification)
        self.db.flush()
        return verification

    def find_latest_by_email_and_code(self, email: str, code: str) -> EmailVerification | None:
        """
        이메일과 코드로 최신 인증 코드 조회

        사용자가 입력한 인증 코드를 검증하기 위해
        해당 이메일의 최신 코드를 조회합니다.

        Args:
            email: 인증 이메일 주소
            code: 검증할 인증 코드

        Returns:
            EmailVerification | None: 일치하는 최신 인증 코드 또는 None
        """
        return self.db.query(EmailVerification).filter(
            EmailVerification.email == email,
            EmailVerification.code == code
        ).order_by(
            EmailVerification.id.desc()
        ).first()

    def find_latest_verified_unused_by_email(
        self,
        email: str,
        now: datetime
    ) -> EmailVerification | None:
        """
        이메일의 검증된 미사용 인증 코드 조회

        회원가입 시 이메일 인증이 완료되었는지 확인하기 위해
        검증이 완료되었지만 아직 사용되지 않은 코드를 조회합니다.

        Args:
            email: 인증 이메일 주소
            now: 현재 시간 (UTC, 만료 체크용)

        Returns:
            EmailVerification | None: 사용 가능한 인증 코드 또는 None

        조회 조건:
            - 검증 완료 (verified_at IS NOT NULL)
            - 아직 사용되지 않음 (used_at IS NULL)
            - 만료되지 않음 (expires_at > now)
        """
        return self.db.query(EmailVerification).filter(
            EmailVerification.email == email,
            EmailVerification.verified_at.is_not(None),
            EmailVerification.used_at.is_(None),
            EmailVerification.expires_at > now
        ).order_by(
            EmailVerification.id.desc()
        ).first()

    def mark_verified(self, verification: EmailVerification, verified_at: datetime) -> EmailVerification:
        """
        인증 코드를 검증 완료 상태로 표시

        사용자가 올바른 인증 코드를 입력했을 때
        검증 완료 시간을 기록합니다.

        Args:
            verification: 검증 완료할 인증 코드 엔티티
            verified_at: 검증 완료 시간 (UTC)

        Returns:
            EmailVerification: 업데이트된 인증 코드 엔티티
        """
        verification.verified_at = verified_at
        self.db.flush()
        return verification

    def mark_used(self, verification: EmailVerification, used_at: datetime) -> EmailVerification:
        """
        인증 코드를 사용 완료 상태로 표시

        회원가입이 성공적으로 완료되었을 때
        인증 코드를 사용 완료 상태로 처리하여 재사용을 방지합니다.

        Args:
            verification: 사용 완료할 인증 코드 엔티티
            used_at: 사용 완료 시간 (UTC)

        Returns:
            EmailVerification: 업데이트된 인증 코드 엔티티
        """
        verification.used_at = used_at
        self.db.flush()
        return verification
