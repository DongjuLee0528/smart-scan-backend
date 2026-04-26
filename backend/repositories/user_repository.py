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
        """
        카카오 사용자 ID로 사용자 조회

        카카오 로그인 시 사용자 식별과 챗봇 서비스 연동에 사용됩니다.

        Args:
            kakao_user_id: 카카오 고유 사용자 식별자

        Returns:
            Optional[User]: 일치하는 사용자 또는 None
        """
        return self.db.query(User).filter(User.kakao_user_id == kakao_user_id).first()

    def find_by_id(self, user_id: int) -> Optional[User]:
        """
        사용자 ID로 사용자 조회

        Args:
            user_id: 조회할 사용자의 고유 ID

        Returns:
            Optional[User]: 일치하는 사용자 또는 None
        """
        return self.db.query(User).filter(User.id == user_id).first()

    def find_by_email(self, email: str) -> Optional[User]:
        """
        이메일 주소로 사용자 조회

        로그인 시 이메일 기반 사용자 인증에 사용됩니다.

        Args:
            email: 조회할 사용자의 이메일 주소

        Returns:
            Optional[User]: 일치하는 사용자 또는 None
        """
        return self.db.query(User).filter(User.email == email).first()

    def find_by_phone(self, phone: str) -> Optional[User]:
        """
        전화번호로 사용자 조회

        Args:
            phone: 조회할 사용자의 전화번호

        Returns:
            Optional[User]: 일치하는 사용자 또는 None
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
        새 사용자 생성 (카카오 ID 필수, 나머지 선택사항)

        Args:
            kakao_user_id: 카카오 고유 사용자 식별자 (필수)
            name: 사용자 이름 (선택사항)
            email: 이메일 주소 (선택사항)
            password_hash: 해시된 비밀번호 (선택사항)
            phone: 전화번호 (선택사항)
            age: 나이 (선택사항)

        Returns:
            User: 생성된 사용자 엔티티
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
        사용자 프로필 정보 업데이트 (회원가입 완성 시 사용)

        Args:
            user: 업데이트할 사용자 엔티티
            name: 새로운 사용자 이름
            email: 새로운 이메일 주소
            password_hash: 새로운 해시된 비밀번호 (선택사항)
            phone: 새로운 전화번호 (선택사항)
            age: 새로운 나이 (선택사항)

        Returns:
            User: 업데이트된 사용자 엔티티
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
        카카오 사용자 조회 또는 신규 생성 (소셜 로그인 시 사용)

        Args:
            kakao_user_id: 카카오 고유 사용자 식별자

        Returns:
            User: 기존 사용자 또는 새로 생성된 사용자
        """
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
