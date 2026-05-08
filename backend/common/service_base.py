"""
Service base class

Base service class that provides common functionality for SmartScan business logic.
All service classes inherit from this to easily query user, family, and family member information.

Main features:
- Extract actor context from user ID
- Verify family member permissions
- Manage common repository instances

Usage pattern: Template Method Pattern
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