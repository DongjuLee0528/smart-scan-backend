"""
JWT refresh token data access layer

Database access layer for secure management of refresh tokens in Smart Scan system JWT authentication.
Implements secure authentication system through token rotation, session management, and security enhancement.

Main features:
- Refresh token generation and lookup
- Token invalidation and rotation management
- User-specific total session invalidation (logout)
- Expired token cleanup and security management

Business rules:
- Immediately invalidate token when used and issue new token (rotation)
- Invalidate all active tokens for user on logout
- Expired tokens automatically invalidated to prevent reuse
- Total session invalidation possible when token theft detected

Security enhancement:
- UUID-based unique token ID ensures unpredictability
- Time-based expiration limits token lifecycle
- Immediate token blocking through invalidation flag
- User-specific token tracking for abnormal access detection

Data flow:
1. Login success → Generate new refresh token
2. Access token expiry → Reissue with refresh token
3. Token usage → Invalidate existing token and issue new token
4. Logout → Invalidate all active tokens
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from backend.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    """
    Refresh token data access class

    Provides CRUD operations and security-related business logic for refresh tokens.
    """
    def __init__(self, db: Session):
        """Inject database session"""
        self.db = db

    def find_by_token_id(self, token_id: str) -> Optional[RefreshToken]:
        """
        Lookup refresh token by token ID

        Used to verify refresh token submitted for access token reissue request.

        Args:
            token_id: Unique identifier of token to lookup (UUID)

        Returns:
            Optional[RefreshToken]: Matching refresh token or None
        """
        return self.db.query(RefreshToken).filter(RefreshToken.token_id == token_id).first()

    def revoke_all_active_by_user_id(self, user_id: int, revoked_at: datetime) -> None:
        """
        Invalidate all active refresh tokens for user

        Immediately terminates all active sessions for the user on logout or security incident.

        Args:
            user_id: User ID to invalidate tokens for
            revoked_at: Token invalidation time (UTC)

        Business logic:
            - Targets all tokens where is_revoked is False
            - Performance optimization through batch update
            - Security audit support by recording invalidation time
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
        Create new refresh token

        Generates new refresh token for successful login or token rotation.

        Args:
            user_id: Token owner user ID
            token_id: Unique token identifier (UUID)
            created_at: Token creation time (UTC)
            expires_at: Token expiration time (UTC)

        Returns:
            RefreshToken: Created refresh token entity

        Security considerations:
            - token_id generated as UUID for unpredictability
            - Minimize security risk with appropriate expiration time
            - Set as active state from creation time
        """
        refresh_token = RefreshToken(
            user_id=user_id,
            token_id=token_id,
            created_at=created_at,
            expires_at=expires_at,
            is_revoked=False  # New tokens created in active state
        )
        self.db.add(refresh_token)
        self.db.flush()
        return refresh_token

    def revoke(self, refresh_token: RefreshToken, revoked_at: datetime) -> RefreshToken:
        """
        Invalidate specific refresh token

        Invalidates specific token for token rotation or individual session termination.

        Args:
            refresh_token: Refresh token entity to invalidate
            revoked_at: Token invalidation time (UTC)

        Returns:
            RefreshToken: Updated refresh token entity

        Usage scenarios:
            - Invalidate existing token during token rotation
            - Block specific token when suspicious activity detected
            - Individual session termination by user request
        """
        refresh_token.is_revoked = True
        refresh_token.revoked_at = revoked_at
        self.db.flush()
        return refresh_token
