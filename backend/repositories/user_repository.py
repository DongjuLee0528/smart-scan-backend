from sqlalchemy.orm import Session
from backend.models.user import User
from typing import Optional


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_kakao_user_id(self, kakao_user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.kakao_user_id == kakao_user_id).first()

    def find_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def find_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def create(
        self,
        kakao_user_id: str,
        name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        age: int | None = None
    ) -> User:
        user = User(
            kakao_user_id=kakao_user_id,
            name=name,
            email=email,
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
        phone: str | None = None,
        age: int | None = None
    ) -> User:
        user.name = name
        user.email = email
        user.phone = phone
        user.age = age
        self.db.flush()
        return user

    def get_or_create(self, kakao_user_id: str) -> User:
        user = self.find_by_kakao_user_id(kakao_user_id)
        if not user:
            user = self.create(kakao_user_id)
        return user
