from sqlalchemy.orm import Session, joinedload
from backend.models.user_device import UserDevice
from backend.models.user import User
from typing import Optional


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

    def create(self, user_id: int, device_id: int) -> UserDevice:
        user_device = UserDevice(user_id=user_id, device_id=device_id)
        self.db.add(user_device)
        self.db.flush()
        return user_device

    def delete(self, user_device: UserDevice) -> None:
        self.db.delete(user_device)
        self.db.flush()
