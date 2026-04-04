from sqlalchemy.orm import Session
from backend.models.family import Family


class FamilyRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, family_name: str, owner_user_id: int) -> Family:
        family = Family(family_name=family_name, owner_user_id=owner_user_id)
        self.db.add(family)
        self.db.flush()
        return family

    def find_by_id(self, family_id: int) -> Family | None:
        return self.db.query(Family).filter(Family.id == family_id).first()
