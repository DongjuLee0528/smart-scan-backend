from sqlalchemy.orm import Session
from backend.models.user import User
from typing import Optional


class UserRepository:
    """
    User data access layer

    Repository responsible for CRUD operations on User model.
    Provides basic data access functions including Kakao ID and email-based user lookup, creation, and profile updates.

    Main responsibilities:
    - Database operations on user entities
    - Kakao ID and email-based lookup
    - User creation and profile updates during registration
    """
    def __init__(self, db: Session):
        """Inject database session"""
        self.db = db

    def find_by_kakao_user_id(self, kakao_user_id: str) -> Optional[User]:
        """
        Find user by Kakao user ID

        Used for user identification during Kakao login and chatbot service integration.

        Args:
            kakao_user_id: Kakao unique user identifier

        Returns:
            Optional[User]: Matching user or None
        """
        return self.db.query(User).filter(User.kakao_user_id == kakao_user_id).first()

    def find_by_id(self, user_id: int) -> Optional[User]:
        """
        Query user by user ID

        Args:
            user_id: Unique ID of user to query

        Returns:
            Optional[User]: Matching user or None
        """
        return self.db.query(User).filter(User.id == user_id).first()

    def find_by_email(self, email: str) -> Optional[User]:
        """
        Query user by email address

        Used for email-based user authentication during login.

        Args:
            email: Email address of user to query

        Returns:
            Optional[User]: Matching user or None
        """
        return self.db.query(User).filter(User.email == email).first()

    def find_by_phone(self, phone: str) -> Optional[User]:
        """
        Query user by phone number

        Args:
            phone: Phone number of user to query

        Returns:
            Optional[User]: Matching user or None
        """
        return self.db.query(User).filter(User.phone == phone).first()

    def create(
        self,
        kakao_user_id: str,
        name: str | None = None,
        email: str | None = None,
        password_hash: str | None = None,
        phone: str | None = None,
        age: int | None = None
    ) -> User:
        """
        Create new user (KakaoTalk ID required, others optional)

        Args:
            kakao_user_id: Kakao unique user identifier (required)
            name: User name (optional)
            email: Email address (optional)
            password_hash: Hashed password (optional)
            phone: Phone number (optional)
            age: Age (optional)

        Returns:
            User: Created user entity
        """
        user = User(
            kakao_user_id=kakao_user_id,
            name=name,
            email=email,
            password_hash=password_hash,
            phone=phone,
            age=age
        )
        self.db.add(user)
        self.db.flush()
        return user

    def update_profile(
        self,
        user: User,
        name: str,
        email: str,
        password_hash: str | None = None,
        phone: str | None = None,
        age: int | None = None
    ) -> User:
        """
        Update user profile information (used when completing registration)

        Args:
            user: User entity to update
            name: New user name
            email: New email address
            password_hash: New hashed password (optional)
            phone: New phone number (optional)
            age: New age (optional)

        Returns:
            User: Updated user entity
        """
        user.name = name
        user.email = email
        if password_hash is not None:
            user.password_hash = password_hash
        user.phone = phone
        user.age = age
        self.db.flush()
        return user

    def get_or_create(self, kakao_user_id: str) -> User:
        """
        Query or create new KakaoTalk user (used for social login)

        Args:
            kakao_user_id: Kakao unique user identifier

        Returns:
            User: Existing user or newly created user
        """
        user = self.find_by_kakao_user_id(kakao_user_id)
        if not user:
            user = self.create(kakao_user_id)
        return user

    def update_kakao_user_id(self, user: User, kakao_user_id: str) -> User:
        """
        Update user's kakao_user_id

        Used to replace existing placeholder value (pending_xxx) with actual Kakao UID
        during KakaoTalk account linking (magic link) process.
        UNIQUE constraint is handled at DB level, caller must check for duplicates beforehand.
        """
        user.kakao_user_id = kakao_user_id
        self.db.flush()
        return user
