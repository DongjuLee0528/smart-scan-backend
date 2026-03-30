from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional, List
from backend.models.master_tag import MasterTag


class MasterTagRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_label_id_and_device_id(self, label_id: int, device_id: int) -> Optional[MasterTag]:
        stmt = select(MasterTag).where(
            MasterTag.label_id == label_id,
            MasterTag.device_id == device_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_tag_uid_and_device_id(self, tag_uid: str, device_id: int) -> Optional[MasterTag]:
        stmt = select(MasterTag).where(
            MasterTag.tag_uid == tag_uid,
            MasterTag.device_id == device_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_label_id_by_tag_uid(self, tag_uid: str) -> Optional[int]:
        stmt = select(MasterTag.label_id).where(
            MasterTag.tag_uid == tag_uid
        )
        result = self.db.execute(stmt).scalar_one_or_none()
        return result

    def get_all_by_device_id(self, device_id: int) -> List[MasterTag]:
        stmt = select(MasterTag).where(
            MasterTag.device_id == device_id
        )
        return self.db.execute(stmt).scalars().all()