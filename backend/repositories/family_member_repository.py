from typing import Optional

from sqlalchemy.orm import Session, joinedload

from backend.models.family_member import FamilyMember


class FamilyMemberRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_user_id(self, user_id: int) -> Optional[FamilyMember]:
        return self.db.query(FamilyMember).filter(FamilyMember.user_id == user_id).first()

    def find_by_id(self, family_member_id: int) -> Optional[FamilyMember]:
        return self.db.query(FamilyMember).options(
            joinedload(FamilyMember.user)
        ).filter(FamilyMember.id == family_member_id).first()

    def find_all_by_family_id(self, family_id: int) -> list[FamilyMember]:
        return self.db.query(FamilyMember).options(
            joinedload(FamilyMember.user)
        ).filter(
            FamilyMember.family_id == family_id
        ).order_by(FamilyMember.created_at.asc(), FamilyMember.id.asc()).all()

    def find_by_family_id_and_user_id(self, family_id: int, user_id: int) -> Optional[FamilyMember]:
        return self.db.query(FamilyMember).filter(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == user_id
        ).first()

    def exists_by_user_id(self, user_id: int) -> bool:
        return self.find_by_user_id(user_id) is not None

    def create(self, family_id: int, user_id: int, role: str) -> FamilyMember:
        family_member = FamilyMember(family_id=family_id, user_id=user_id, role=role)
        self.db.add(family_member)
        self.db.flush()
        return family_member

    def delete(self, family_member: FamilyMember) -> None:
        self.db.delete(family_member)
        self.db.flush()
