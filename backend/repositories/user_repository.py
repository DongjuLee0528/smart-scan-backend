from sqlalchemy.orm import Session
from backend.models.user import User
from typing import Optional


class UserRepository:
    """
    사용자 데이터 접근 계층

    사용자(User) 모델에 대한 CRUD 연산을 담당하는 리포지토리.
    카카오 ID와 이메일 기반 사용자 조회, 생성, 프로필 업데이트 등의 기본 데이터 액세스 기능을 제공한다.

    주요 책임:
    - 사용자 엔티티의 데이터베이스 연산
    - 카카오 ID 및 이메일 기반 조회
    - 회원가입 시 사용자 생성 및 프로필 업데이트
    """
    def __init__(self, db: Session):
        self.db = db

    def find_by_kakao_user_id(self, kakao_user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.kakao_user_id == kakao_user_id).first()

    def find_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def find_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def find_by_phone(self, phone: str) -> Optional[User]:
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
        user.name = name
        user.email = email
        if password_hash is not None:
            user.password_hash = password_hash
        user.phone = phone
        user.age = age
        self.db.flush()
        return user

    def get_or_create(self, kakao_user_id: str) -> User:
        user = self.find_by_kakao_user_id(kakao_user_id)
        if not user:
            user = self.create(kakao_user_id)
        return user

    def update_kakao_user_id(self, user: User, kakao_user_id: str) -> User:
        """
        사용자의 kakao_user_id 업데이트

        카카오 계정 연동(magic link) 과정에서 기존 placeholder 값(pending_xxx)을
        실제 카카오 UID 로 교체하기 위해 사용한다.
        UNIQUE 제약은 DB 수준에서 처리되며, 호출 측에서 사전에 중복을 확인해야 한다.
        """
        user.kakao_user_id = kakao_user_id
        self.db.flush()
        return user
