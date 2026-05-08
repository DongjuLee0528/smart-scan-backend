"""
AuthService.link_kakao unit tests

Run:
  cd smart-scan-backend
  pytest backend/tests/test_link_kakao.py -v

Test coverage:
- Successful linking (pending_ placeholder → actual UID)
- Idempotent handling (already linked with same UID)
- Invalid token → UnauthorizedException
- Non-existent user → NotFoundException
- UID already taken by another user → ConflictException
- User already linked with real UID → ConflictException
- Empty token → BadRequestException
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
    # EmailService cannot initialize without SMTP → use mock
    with patch("backend.services.auth_service.EmailService"):
        svc = AuthService(db)
    return svc


def _make_user(user_id: int = 1, kakao_user_id: str = "pending_abc", email: str = "user@test.com"):
    u = MagicMock()
    u.id = user_id
    u.email = email
    u.name = "Tester"
    u.kakao_user_id = kakao_user_id
    return u


def _valid_token(kakao_user_id: str = "real_kakao_uid_12345") -> str:
    """Generate valid JWT signed with actual create_kakao_link_token"""
    token, _ = create_kakao_link_token(kakao_user_id)
    return token


# ── Success Cases ────────────────────────────────────────────────────────────────

class TestLinkKakaoSuccess:
    def test_pending_user_can_link(self, service):
        """User in pending_ state can link with valid token and returns linked=True."""
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
        """User with None kakao_user_id can also link successfully."""
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
        """If already linked with the same kakao_user_id, returns idempotent success without commit."""
        user = _make_user(kakao_user_id="real_kakao_uid_12345")
        service.user_repository.find_by_id = MagicMock(return_value=user)
        # Replace with mock for verification (confirm not called in idempotent path)
        service.user_repository.update_kakao_user_id = MagicMock()

        result = service.link_kakao(user.id, _valid_token("real_kakao_uid_12345"))

        assert result.linked is True
        assert result.kakao_user_id == "real_kakao_uid_12345"
        # Idempotent: no commit or update calls
        service.db.commit.assert_not_called()
        service.user_repository.update_kakao_user_id.assert_not_called()


# ── Error Cases ───────────────────────────────────────────────────────────────

class TestLinkKakaoErrors:
    def test_invalid_jwt_raises_unauthorized(self, service):
        """Invalid JWT signature raises UnauthorizedException."""
        with pytest.raises(UnauthorizedException):
            service.link_kakao(1, "this.is.not.a.valid.jwt")

    def test_empty_token_raises_bad_request(self, service):
        """Empty token string raises BadRequestException."""
        with pytest.raises(BadRequestException):
            service.link_kakao(1, "   ")

    def test_user_not_found_raises_not_found(self, service):
        """Non-existent user_id raises NotFoundException."""
        service.user_repository.find_by_id = MagicMock(return_value=None)

        with pytest.raises(NotFoundException):
            service.link_kakao(999, _valid_token())

    def test_conflict_another_user_owns_uid(self, service):
        """ConflictException when another user already owns the same kakao_user_id."""
        user = _make_user(user_id=1, kakao_user_id="pending_abc")
        other = _make_user(user_id=2, kakao_user_id="real_kakao_uid_12345")
        service.user_repository.find_by_id = MagicMock(return_value=user)
        service.user_repository.find_by_kakao_user_id = MagicMock(return_value=other)

        with pytest.raises(ConflictException, match="another user"):
            service.link_kakao(1, _valid_token("real_kakao_uid_12345"))

    def test_conflict_already_linked_real_uid(self, service):
        """ConflictException when current user is already linked with real UID (non-pending)."""
        user = _make_user(kakao_user_id="already_real_uid")
        service.user_repository.find_by_id = MagicMock(return_value=user)
        service.user_repository.find_by_kakao_user_id = MagicMock(return_value=None)

        with pytest.raises(ConflictException, match="already linked"):
            service.link_kakao(1, _valid_token("different_real_uid"))

    def test_no_rollback_on_success(self, service):
        """No rollback is called on successful processing."""
        user = _make_user(kakao_user_id="pending_xyz")
        service.user_repository.find_by_id = MagicMock(return_value=user)
        service.user_repository.find_by_kakao_user_id = MagicMock(return_value=None)
        service.user_repository.update_kakao_user_id = MagicMock(
            side_effect=lambda u, kid: setattr(u, "kakao_user_id", kid)
        )

        service.link_kakao(1, _valid_token("brand_new_uid"))

        service.db.rollback.assert_not_called()
