"""
Family member data access layer

Repository that manages family member information in Smart Scan system.
Manages connection information and roles between families and users.

Data management:
- Add/remove family members
- Member role and permission management
- Retrieve member lists by family

Business rules:
- owner: Family owner with full permissions
- member: Regular family member with limited permissions
- Only one owner per family allowed

Main use cases:
- Register as family owner during user registration
- Add new members during family invitation
- Family-level data access permission verification
"""

from typing import Optional

from sqlalchemy.orm import Session, joinedload

from backend.models.family_member import FamilyMember


class FamilyMemberRepository:
    """
    Family member data access layer

    Repository responsible for CRUD operations on FamilyMember model.
    Provides connection information and role management between families and users.

    Main responsibilities:
    - Database operations on family member entities
    - User and family mapping management
    - Role and permission management within families
    """
    def __init__(self, db: Session):
        """Inject database session"""
        self.db = db

    def find_by_user_id(self, user_id: int) -> Optional[FamilyMember]:
        """Query family member information by user ID"""
        return self.db.query(FamilyMember).filter(FamilyMember.user_id == user_id).first()

    def find_by_id(self, family_member_id: int) -> Optional[FamilyMember]:
        """Query by family member ID (includes user information)"""
        return self.db.query(FamilyMember).options(
            joinedload(FamilyMember.user)
        ).filter(FamilyMember.id == family_member_id).first()

    def find_all_by_family_id(self, family_id: int) -> list[FamilyMember]:
        """Query all member list of family (includes user information)"""
        return self.db.query(FamilyMember).options(
            joinedload(FamilyMember.user)
        ).filter(
            FamilyMember.family_id == family_id
        ).order_by(FamilyMember.created_at.asc(), FamilyMember.id.asc()).all()

    def find_by_family_id_and_user_id(self, family_id: int, user_id: int) -> Optional[FamilyMember]:
        """Query member information by family ID and user ID"""
        return self.db.query(FamilyMember).filter(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == user_id
        ).first()

    def exists_by_user_id(self, user_id: int) -> bool:
        """Check whether user belongs to family"""
        return self.find_by_user_id(user_id) is not None

    def create(self, family_id: int, user_id: int, role: str) -> FamilyMember:
        """Create new family member"""
        family_member = FamilyMember(family_id=family_id, user_id=user_id, role=role)
        self.db.add(family_member)
        self.db.flush()
        return family_member

    def delete(self, family_member: FamilyMember) -> None:
        """Delete family member"""
        self.db.delete(family_member)
        self.db.flush()
