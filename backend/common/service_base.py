"""
서비스 기본 클래스

SmartScan 비즈니스 로직의 공통 기능을 제공하는 기본 서비스 클래스입니다.
모든 서비스 클래스가 상속하여 사용자, 가족, 가족구성원 정보를 쉽게 조회할 수 있습니다.

주요 기능:
- 사용자 ID로부터 액터 컨텍스트 추출
- 가족 구성원 권한 확인
- 공통 레포지토리 인스턴스 관리

사용 패턴: Template Method Pattern
"""

from sqlalchemy.orm import Session

from backend.common.exceptions import BadRequestException, NotFoundException
from backend.repositories.family_member_repository import FamilyMemberRepository
from backend.repositories.family_repository import FamilyRepository
from backend.repositories.user_repository import UserRepository


class ServiceBase:
    """Base service class with common actor context resolution"""

    def __init__(self, db: Session):
        self.db = db
        self.user_repository = UserRepository(db)
        self.family_repository = FamilyRepository(db)
        self.family_member_repository = FamilyMemberRepository(db)

    def _get_actor_context(self, user_id: int):
        """Get actor, family_member, and family from user_id"""
        actor = self.user_repository.find_by_id(user_id)
        if not actor:
            raise NotFoundException("User not found")

        family_member = self.family_member_repository.find_by_user_id(actor.id)
        if not family_member:
            raise BadRequestException("User is not assigned to a family")

        family = self.family_repository.find_by_id(family_member.family_id)
        if not family:
            raise NotFoundException("Family not found")

        return actor, family_member, family