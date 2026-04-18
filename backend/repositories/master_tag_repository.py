"""
마스터 태그 데이터 접근 계층

실제 물리적 RFID 태그의 데이터베이스 작업을 담당하는 레포지토리입니다.
디바이스에 부착된 물리적 태그의 메타데이터를 관리합니다.

데이터 관리:
- 물리적 태그 정보 (태그 UID, 라벨 ID)
- 디바이스별 태그 매핑 정보
- 라벨 기반 태그 분류 및 조회

비즈니스 규칙:
- 태그 UID는 전체 시스템에서 고유해야 함
- 마스터 태그는 특정 디바이스에만 속해있음
- 라벨 ID를 통해 아이템 등록 시 카테고리 분류
- 아이템과 1:1 매칭되어 위치 추적에 사용

주요 사용 케이스:
- 사용자가 아이템 등록 시 라벨 기반 태그 찾기
- RFID 스캔 데이터 처리 시 태그 UID 매칭
- 디바이스별 등록된 태그 목록 관리
"""

from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional, List
from backend.models.master_tag import MasterTag


class MasterTagRepository:
    """
    마스터 태그 데이터 접근 클래스

    물리적 RFID 태그 정보에 대한 CRUD 작업을 제공합니다.
    """
    def __init__(self, db: Session):
        """데이터베이스 세션 주입"""
        self.db = db

    def get_by_label_id_and_device_id(self, label_id: int, device_id: int) -> Optional[MasterTag]:
        """라벨 ID와 디바이스 ID로 마스터 태그 조회 (아이템 등록 시 사용)"""
        stmt = select(MasterTag).where(
            MasterTag.label_id == label_id,
            MasterTag.device_id == device_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_tag_uid_and_device_id(self, tag_uid: str, device_id: int) -> Optional[MasterTag]:
        """태그 UID와 디바이스 ID로 마스터 태그 조회 (아이템 수정 시 사용)"""
        stmt = select(MasterTag).where(
            MasterTag.tag_uid == tag_uid,
            MasterTag.device_id == device_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_label_id_by_tag_uid(self, tag_uid: str) -> Optional[int]:
        """태그 UID로 라벨 ID만 조회 (빠른 매칭용)"""
        stmt = select(MasterTag.label_id).where(
            MasterTag.tag_uid == tag_uid
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_all_by_device_id(self, device_id: int) -> List[MasterTag]:
        """디바이스의 모든 마스터 태그 목록 조회"""
        stmt = select(MasterTag).where(
            MasterTag.device_id == device_id
        )
        return self.db.execute(stmt).scalars().all()
