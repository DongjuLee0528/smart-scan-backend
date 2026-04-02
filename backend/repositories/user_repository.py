from sqlalchemy.orm import Session
from backend.models.user import User
from typing import Optional


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_kakao_user_id(self, kakao_user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.kakao_user_id == kakao_user_id).first()

    def create(self, kakao_user_id: str) -> User:
        user = User(kakao_user_id=kakao_user_id)
        self.db.add(user)
        self.db.flush()
        return user

    def get_or_create(self, kakao_user_id: str) -> User:
        user = self.find_by_kakao_user_id(kakao_user_id)
        if not user:
            user = self.create(kakao_user_id)
        return user
