"""
Family group data access layer

Repository that manages family group data in SmartScan system.
Core concept of SmartScan where devices and belongings are shared at family level.

Data management:
- Family group creation and metadata management
- Family owner and member permission management
- Family name, description, and settings storage

Business rules:
- Only family owners can delete families and change major settings
- All associated data (members, devices, items) cascade delete when family is deleted
- Family names don't need to be unique within owner scope

Main use cases:
- Create default family during user registration
- Family member invitation and member permission verification
- Family-level data access control
"""

from sqlalchemy.orm import Session
from backend.models.family import Family


class FamilyRepository:
    """
    Family group data access class

    Provides CRUD operations and family management business logic for family table.
    """
    def __init__(self, db: Session):
        self.db = db

    def create(self, family_name: str, owner_user_id: int) -> Family:
        """
        Create new family group

        Creates new family group during user registration or manually.
        Creator automatically becomes family owner.
        """
        family = Family(family_name=family_name, owner_user_id=owner_user_id)
        self.db.add(family)
        self.db.flush()
        return family

    def find_by_id(self, family_id: int) -> Family | None:
        """
        Find family group by family ID

        Args:
            family_id: Unique ID of family to find

        Returns:
            Family | None: Matching family group or None
        """
        return self.db.query(Family).filter(Family.id == family_id).first()
