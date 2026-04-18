"""
JWT 리프레시 토큰 데이터 접근 계층

Smart Scan 시스템의 JWT 인증에서 리프레시 토큰의 안전한 관리를 위한 데이터베이스 접근 계층입니다.
토큰 로테이션, 세션 관리, 보안 강화를 통해 안전한 인증 시스템을 구현합니다.

주요 기능:
- 리프레시 토큰 생성 및 조회
- 토큰 무효화 및 로테이션 관리
- 사용자별 전체 세션 무효화 (로그아웃)
- 만료된 토큰 정리 및 보안 관리

비즈니스 규칙:
- 토큰 사용 시 즉시 무효화하고 새 토큰 발급 (로테이션)
- 로그아웃 시 해당 사용자의 모든 활성 토큰 무효화
- 만료된 토큰은 자동으로 무효화되어 재사용 방지
- 토큰 탈취 감지 시 전체 세션 무효화 가능

보안 강화:
- UUID 기반 고유 토큰 ID로 예측 불가능성 확보
- 시간 기반 만료로 토큰 생명주기 제한
- 무효화 플래그를 통한 즉시 토큰 차단
- 사용자별 토큰 추적으로 비정상 접근 감지

데이터 흐름:
1. 로그인 성공 → 새 리프레시 토큰 생성
2. 액세스 토큰 만료 → 리프레시 토큰으로 재발급
3. 토큰 사용 → 기존 토큰 무효화 및 새 토큰 발급
4. 로그아웃 → 모든 활성 토큰 무효화
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    """
    리프레시 토큰 데이터 접근 클래스

    리프레시 토큰의 CRUD 작업과 보안 관련 비즈니스 로직을 제공합니다.
    """
    def __init__(self, db: Session):
        """데이터베이스 세션 주입"""
        self.db = db

    def find_by_token_id(self, token_id: str) -> Optional[RefreshToken]:
        """
        토큰 ID로 리프레시 토큰 조회

        액세스 토큰 재발급 요청 시 제출된 리프레시 토큰을 검증하기 위해 사용합니다.

        Args:
            token_id: 조회할 토큰의 고유 식별자 (UUID)

        Returns:
            Optional[RefreshToken]: 일치하는 리프레시 토큰 또는 None
        """
        return self.db.query(RefreshToken).filter(RefreshToken.token_id == token_id).first()

    def revoke_all_active_by_user_id(self, user_id: int, revoked_at: datetime) -> None:
        """
        사용자의 모든 활성 리프레시 토큰 무효화

        로그아웃 또는 보안 사고 시 해당 사용자의 모든 활성 세션을 즉시 종료합니다.

        Args:
            user_id: 토큰을 무효화할 사용자 ID
            revoked_at: 토큰 무효화 시간 (UTC)

        비즈니스 로직:
            - is_revoked가 False인 모든 토큰을 대상으로 함
            - 일괄 업데이트로 성능 최적화
            - 무효화 시간 기록으로 보안 감사 지원
        """
        self.db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked.is_(False)
        ).update(
            {
                RefreshToken.is_revoked: True,
                RefreshToken.revoked_at: revoked_at
            },
            synchronize_session=False
        )

    def create(
        self,
        user_id: int,
        token_id: str,
        created_at: datetime,
        expires_at: datetime
    ) -> RefreshToken:
        """
        새 리프레시 토큰 생성

        로그인 성공 또는 토큰 로테이션 시 새로운 리프레시 토큰을 생성합니다.

        Args:
            user_id: 토큰 소유자 사용자 ID
            token_id: 고유 토큰 식별자 (UUID)
            created_at: 토큰 생성 시간 (UTC)
            expires_at: 토큰 만료 시간 (UTC)

        Returns:
            RefreshToken: 생성된 리프레시 토큰 엔티티

        보안 고려사항:
            - token_id는 UUID로 예측 불가능하게 생성
            - 적절한 만료 시간 설정으로 보안 위험 최소화
            - 생성 시점부터 활성 상태로 설정
        """
        refresh_token = RefreshToken(
            user_id=user_id,
            token_id=token_id,
            created_at=created_at,
            expires_at=expires_at,
            is_revoked=False  # 새 토큰은 활성 상태로 생성
        )
        self.db.add(refresh_token)
        self.db.flush()
        return refresh_token

    def revoke(self, refresh_token: RefreshToken, revoked_at: datetime) -> RefreshToken:
        """
        특정 리프레시 토큰 무효화

        토큰 로테이션이나 개별 세션 종료 시 특정 토큰을 무효화합니다.

        Args:
            refresh_token: 무효화할 리프레시 토큰 엔티티
            revoked_at: 토큰 무효화 시간 (UTC)

        Returns:
            RefreshToken: 업데이트된 리프레시 토큰 엔티티

        사용 시나리오:
            - 토큰 로테이션 시 기존 토큰 무효화
            - 의심스러운 활동 감지 시 해당 토큰 차단
            - 사용자 요청에 의한 개별 세션 종료
        """
        refresh_token.is_revoked = True
        refresh_token.revoked_at = revoked_at
        self.db.flush()
        return refresh_token
