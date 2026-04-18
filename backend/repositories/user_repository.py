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
        """데이터베이스 세션 주입"""
        self.db = db

    def find_by_kakao_user_id(self, kakao_user_id: str) -> Optional[User]:
        """카카오 사용자 ID로 사용자 조회"""
        return self.db.query(User).filter(User.kakao_user_id == kakao_user_id).first()

    def find_by_id(self, user_id: int) -> Optional[User]:
        """사용자 ID로 사용자 조회"""
        return self.db.query(User).filter(User.id == user_id).first()

    def find_by_email(self, email: str) -> Optional[User]:
        """이메일 주소로 사용자 조회"""
        return self.db.query(User).filter(User.email == email).first()

    def find_by_phone(self, phone: str) -> Optional[User]:
        """전화번호로 사용자 조회"""
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
        """새 사용자 생성 (카카오 ID 필수, 나머지 선택사항)"""
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
        """사용자 프로필 정보 업데이트 (회원가입 완성 시 사용)"""
        user.name = name
        user.email = email
        if password_hash is not None:
            user.password_hash = password_hash
        user.phone = phone
        user.age = age
        self.db.flush()
        return user

    def get_or_create(self, kakao_user_id: str) -> User:
        """카카오 사용자 조회 또는 신규 생성 (소셜 로그인 시 사용)"""
        user = self.find_by_kakao_user_id(kakao_user_id)
        if not user:
            user = self.create(kakao_user_id)
        return user
