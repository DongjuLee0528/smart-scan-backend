from typing import Optional

from sqlalchemy.orm import Session, joinedload

from backend.models.user import User
from backend.models.user_device import UserDevice


class UserDeviceRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_user_and_device(self, user_id: int, device_id: int) -> Optional[UserDevice]:
        return self.db.query(UserDevice).options(
            joinedload(UserDevice.device)
        ).filter(
            UserDevice.user_id == user_id,
            UserDevice.device_id == device_id
        ).first()

    def find_by_user_id(self, user_id: int) -> Optional[UserDevice]:
        return self.db.query(UserDevice).options(
            joinedload(UserDevice.device)
        ).filter(UserDevice.user_id == user_id).first()

    def get_by_kakao_user_id(self, kakao_user_id: str) -> Optional[UserDevice]:
        return self.db.query(UserDevice).join(User).options(
            joinedload(UserDevice.device)
        ).filter(User.kakao_user_id == kakao_user_id).first()

    def find_all_by_device_id(self, device_id: int) -> list[UserDevice]:
        return self.db.query(UserDevice).options(
            joinedload(UserDevice.device)
        ).filter(UserDevice.device_id == device_id).all()

    def find_all_by_user_ids(self, user_ids: list[int]) -> list[UserDevice]:
        if not user_ids:
            return []

        return self.db.query(UserDevice).options(
            joinedload(UserDevice.device)
        ).filter(UserDevice.user_id.in_(user_ids)).all()

    def create(self, user_id: int, device_id: int) -> UserDevice:
        user_device = UserDevice(user_id=user_id, device_id=device_id)
        self.db.add(user_device)
        self.db.flush()
        return user_device

    def delete(self, user_device: UserDevice) -> None:
        self.db.delete(user_device)
        self.db.flush()

    def delete_many(self, user_devices: list[UserDevice]) -> None:
        for user_device in user_devices:
            self.db.delete(user_device)
        self.db.flush()
