"""
사용자-디바이스 데이터 접근 계층

Smart Scan 시스템에서 사용자와 디바이스 간의 연결 정보를 관리하는 레포지토리입니다.
가족 단위로 공유되는 디바이스에 대한 사용자 접근 권한을 관리합니다.

데이터 관리:
- 사용자-디바이스 연결 생성 및 삭제
- 디바이스 등록 상태 및 연결 정보 조회
- 사용자별 디바이스 접근 권한 검증

비즈니스 규칙:
- 한 가족당 하나의 디바이스 공유 사용
- 가족 구성원 전체가 동일 디바이스에 자동 연결
- 디바이스 등록 시 모든 가족 구성원에게 연결 배포
- 디바이스 해제 시 모든 연결 동시 삭제

주요 사용 케이스:
- 가족 디바이스 등록 시 사용자 연결 생성
- 사용자의 디바이스 접근 권한 검증
- 아이템 관리 및 스캔 데이터 처리 시 사용
"""

from typing import Optional

from sqlalchemy.orm import Session, joinedload

from backend.models.user import User
from backend.models.user_device import UserDevice


class UserDeviceRepository:
    """
    사용자-디바이스 연결 데이터 접근 클래스

    사용자와 디바이스 간의 연결 상태 관리를 위한 CRUD 작업을 제공합니다.
    """
    def __init__(self, db: Session):
        """데이터베이스 세션 주입"""
        self.db = db

    def find_by_user_and_device(self, user_id: int, device_id: int) -> Optional[UserDevice]:
        """사용자 ID와 디바이스 ID로 연결 정보 조회"""
        return self.db.query(UserDevice).options(
            joinedload(UserDevice.device)
        ).filter(
            UserDevice.user_id == user_id,
            UserDevice.device_id == device_id
        ).first()

    def find_by_user_id(self, user_id: int) -> Optional[UserDevice]:
        """사용자 ID로 디바이스 연결 정보 조회"""
        return self.db.query(UserDevice).options(
            joinedload(UserDevice.device)
        ).filter(UserDevice.user_id == user_id).first()

    def get_by_kakao_user_id(self, kakao_user_id: str) -> Optional[UserDevice]:
        """카카오 사용자 ID로 디바이스 연결 정보 조회 (람다에서 사용)"""
        return self.db.query(UserDevice).join(User).options(
            joinedload(UserDevice.device)
        ).filter(User.kakao_user_id == kakao_user_id).first()

    def find_all_by_device_id(self, device_id: int) -> list[UserDevice]:
        """디바이스에 연결된 모든 사용자 목록 조회"""
        return self.db.query(UserDevice).options(
            joinedload(UserDevice.device)
        ).filter(UserDevice.device_id == device_id).all()

    def find_all_by_user_ids(self, user_ids: list[int]) -> list[UserDevice]:
        """여러 사용자의 디바이스 연결 정보 목록 조회"""
        if not user_ids:
            return []

        return self.db.query(UserDevice).options(
            joinedload(UserDevice.device)
        ).filter(UserDevice.user_id.in_(user_ids)).all()

    def create(self, user_id: int, device_id: int) -> UserDevice:
        """새 사용자-디바이스 연결 생성"""
        user_device = UserDevice(user_id=user_id, device_id=device_id)
        self.db.add(user_device)
        self.db.flush()
        return user_device

    def delete(self, user_device: UserDevice) -> None:
        """사용자-디바이스 연결 삭제"""
        self.db.delete(user_device)
        self.db.flush()

    def delete_many(self, user_devices: list[UserDevice]) -> None:
        """여러 사용자-디바이스 연결 일괄 삭제"""
        for user_device in user_devices:
            self.db.delete(user_device)
        self.db.flush()