"""
AuthService.link_kakao 유닛 테스트

Run:
  cd smart-scan-backend
  pytest backend/tests/test_link_kakao.py -v

테스트 커버리지:
- 정상 연동 (pending_ placeholder → 실제 UID)
- 멱등 처리 (이미 동일한 UID로 연동된 경우)
- 유효하지 않은 토큰 → UnauthorizedException
- 존재하지 않는 사용자 → NotFoundException
- 다른 사용자가 UID 점유 → ConflictException
- 이미 실제 UID로 연동된 사용자 → ConflictException
- 빈 토큰 → BadRequestException
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.common.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
    UnauthorizedException,
)
from backend.common.security import create_kakao_link_token
from backend.services.auth_service import AuthService


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def db():
    mock_db = MagicMock()
    mock_db.commit = MagicMock()
    mock_db.rollback = MagicMock()
    mock_db.flush = MagicMock()
    mock_db.refresh = MagicMock()
    return mock_db


@pytest.fixture
def service(db):
    # EmailService는 SMTP 없이 초기화 불가 → mock 처리
    with patch("backend.services.auth_service.EmailService"):
        svc = AuthService(db)
    return svc


def _make_user(user_id: int = 1, kakao_user_id: str = "pending_abc", email: str = "user@test.com"):
    u = MagicMock()
    u.id = user_id
    u.email = email
    u.name = "테스터"
    u.kakao_user_id = kakao_user_id
    return u


def _valid_token(kakao_user_id: str = "real_kakao_uid_12345") -> str:
    """실제 create_kakao_link_token으로 서명된 유효한 JWT 생성"""
    token, _ = create_kakao_link_token(kakao_user_id)
    return token


# ── 정상 케이스 ────────────────────────────────────────────────────────────────

class TestLinkKakaoSuccess:
    def test_pending_user_can_link(self, service):
        """pending_ 상태 사용자가 유효한 토큰으로 연동하면 linked=True 반환."""
        user = _make_user(kakao_user_id="pending_12345")
        service.user_repository.find_by_id = MagicMock(return_value=user)
        service.user_repository.find_by_kakao_user_id = MagicMock(return_value=None)

        def _set_uid(u, kid):
            u.kakao_user_id = kid

        service.user_repository.update_kakao_user_id = MagicMock(side_effect=_set_uid)

        result = service.link_kakao(user.id, _valid_token("real_kakao_uid_12345"))

        assert result.linked is True
        assert result.kakao_user_id == "real_kakao_uid_12345"
        assert result.user_id == user.id
        service.db.commit.assert_called_once()

    def test_null_kakao_user_id_can_link(self, service):
        """kakao_user_id가 None인 사용자도 연동 가능하다."""
        user = _make_user(kakao_user_id=None)
        service.user_repository.find_by_id = MagicMock(return_value=user)
        service.user_repository.find_by_kakao_user_id = MagicMock(return_value=None)

        def _set_uid(u, kid):
            u.kakao_user_id = kid

        service.user_repository.update_kakao_user_id = MagicMock(side_effect=_set_uid)

        result = service.link_kakao(user.id, _valid_token("real_uid_9999"))

        assert result.linked is True
        service.db.commit.assert_called_once()

    def test_idempotent_same_uid(self, service):
        """이미 동일한 kakao_user_id로 연동된 경우 commit 없이 멱등 성공."""
        user = _make_user(kakao_user_id="real_kakao_uid_12345")
        service.user_repository.find_by_id = MagicMock(return_value=user)
        # 검증을 위해 mock으로 교체 (멱등 경로에서 호출되지 않음을 확인)
        service.user_repository.update_kakao_user_id = MagicMock()

        result = service.link_kakao(user.id, _valid_token("real_kakao_uid_12345"))

        assert result.linked is True
        assert result.kakao_user_id == "real_kakao_uid_12345"
        # 멱등: commit, update 호출 없음
        service.db.commit.assert_not_called()
        service.user_repository.update_kakao_user_id.assert_not_called()


# ── 에러 케이스 ───────────────────────────────────────────────────────────────

class TestLinkKakaoErrors:
    def test_invalid_jwt_raises_unauthorized(self, service):
        """서명이 잘못된 JWT이면 UnauthorizedException을 발생시킨다."""
        with pytest.raises(UnauthorizedException):
            service.link_kakao(1, "this.is.not.a.valid.jwt")

    def test_empty_token_raises_bad_request(self, service):
        """빈 문자열 토큰이면 BadRequestException을 발생시킨다."""
        with pytest.raises(BadRequestException):
            service.link_kakao(1, "   ")

    def test_user_not_found_raises_not_found(self, service):
        """존재하지 않는 user_id이면 NotFoundException을 발생시킨다."""
        service.user_repository.find_by_id = MagicMock(return_value=None)

        with pytest.raises(NotFoundException):
            service.link_kakao(999, _valid_token())

    def test_conflict_another_user_owns_uid(self, service):
        """다른 사용자가 동일한 kakao_user_id를 이미 점유하면 ConflictException."""
        user = _make_user(user_id=1, kakao_user_id="pending_abc")
        other = _make_user(user_id=2, kakao_user_id="real_kakao_uid_12345")
        service.user_repository.find_by_id = MagicMock(return_value=user)
        service.user_repository.find_by_kakao_user_id = MagicMock(return_value=other)

        with pytest.raises(ConflictException, match="another user"):
            service.link_kakao(1, _valid_token("real_kakao_uid_12345"))

    def test_conflict_already_linked_real_uid(self, service):
        """현재 사용자가 이미 실제 UID(non-pending)로 연동되어 있으면 ConflictException."""
        user = _make_user(kakao_user_id="already_real_uid")
        service.user_repository.find_by_id = MagicMock(return_value=user)
        service.user_repository.find_by_kakao_user_id = MagicMock(return_value=None)

        with pytest.raises(ConflictException, match="already linked"):
            service.link_kakao(1, _valid_token("different_real_uid"))

    def test_no_rollback_on_success(self, service):
        """정상 처리 시 rollback이 호출되지 않는다."""
        user = _make_user(kakao_user_id="pending_xyz")
        service.user_repository.find_by_id = MagicMock(return_value=user)
        service.user_repository.find_by_kakao_user_id = MagicMock(return_value=None)
        service.user_repository.update_kakao_user_id = MagicMock(
            side_effect=lambda u, kid: setattr(u, "kakao_user_id", kid)
        )

        service.link_kakao(1, _valid_token("brand_new_uid"))

        service.db.rollback.assert_not_called()
