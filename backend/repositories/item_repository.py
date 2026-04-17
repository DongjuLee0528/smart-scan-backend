"""
아이템 데이터 접근 계층

태그와 연결된 실제 물건(아이템)의 데이터베이스 작업을 담당하는 레포지토리입니다.
라벨 정보와 함께 아이템 조회, 생성, 수정, 연삭제 기능을 제공합니다.

데이터 관리:
- 아이템 메타데이터 (이름, 설명, 등록일 등)
- 태그 UID를 통한 물리적 태그와의 연결
- 라벨 기반 아이템 분류 및 조회
- 사용자 디바이스별 아이템 관리

비즈니스 규칙:
- 하나의 태그 UID에는 하나의 활성 아이템만 연결 가능
- 사용자는 본인이 등록한 아이템만 수정/삭제 가능
- 가족 구성원은 서로의 아이템 조회 가능 (읽기 전용)
- 아이템 삭제 시 연관된 스캔 로그 존재 여부 확인 필요

주요 사용 케이스:
- 사용자가 신규 소지품 등록 시 아이템 생성
- 가족 구성원의 전체 소지품 목록 조회
- 태그 스캔 시 연결된 아이템 정보 검색
- 라벨별 아이템 분류 및 통계
"""

from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from typing import List, Optional, Set, Tuple
from backend.models.device import Device
from backend.models.item import Item
from backend.models.master_tag import MasterTag
from backend.models.user_device import UserDevice


class ItemRepository:
    """
    아이템 데이터 접근 계층

    태그와 연결된 실제 물건(아이템)의 데이터베이스 연산을 담당한다.
    라벨 정보와 함께 아이템 조회, 생성, 수정, 연삭제 기능을 제공한다.

    주요 책임:
    - 아이템 엔티티의 CRUD 연산
    - 태그 UID 기반 조회 및 중복 검사
    - 라벨과 연결된 아이템 목록 제공
    - 가족 단위 아이템 관리
    """
    def __init__(self, db: Session):
        """데이터베이스 세션 주입"""
        self.db = db

    def get_active_items_by_user_device_id(self, user_device_id: int) -> List[Item]:
        """사용자 디바이스의 활성 아이템 목록 조회"""
        stmt = select(Item).where(
            and_(
                Item.user_device_id == user_device_id,
                Item.is_active == True
            )
        ).order_by(Item.created_at.desc())
        return self.db.execute(stmt).scalars().all()

    def get_active_items_by_user_device_ids(self, user_device_ids: List[int]) -> List[Item]:
        """여러 사용자 디바이스의 활성 아이템 목록 조회"""
        if not user_device_ids:
            return []

        stmt = select(Item).where(
            and_(
                Item.user_device_id.in_(user_device_ids),
                Item.is_active == True
            )
        ).order_by(Item.created_at.desc(), Item.id.desc())
        return self.db.execute(stmt).scalars().all()

    def get_active_items_with_label_by_user_device_id(self, user_device_id: int) -> List[Tuple[Item, int]]:
        """사용자 디바이스의 활성 아이템과 라벨 정보 함께 조회"""
        stmt = select(Item, MasterTag.label_id).join(
            MasterTag,
            Item.tag_uid == MasterTag.tag_uid
        ).where(
            and_(
                Item.user_device_id == user_device_id,
                Item.is_active == True
            )
        ).order_by(Item.created_at.desc())
        return self.db.execute(stmt).all()

    def get_by_id(self, item_id: int) -> Optional[Item]:
        """아이템 ID로 조회"""
        stmt = select(Item).where(Item.id == item_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_user_device_and_tag_uid(self, user_device_id: int, tag_uid: str) -> Optional[Item]:
        """사용자 디바이스와 태그 UID로 아이템 조회"""
        stmt = select(Item).where(
            and_(
                Item.user_device_id == user_device_id,
                Item.tag_uid == tag_uid,
                Item.is_active == True
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_family_id_and_tag_uid(
        self,
        family_id: int,
        tag_uid: str,
        exclude_item_id: Optional[int] = None
    ) -> Optional[Item]:
        """가족 내 태그 UID 중복 사용 검사 (수정 시 자기 제외 가능)"""
        stmt = select(Item).join(
            UserDevice,
            Item.user_device_id == UserDevice.id
        ).join(
            Device,
            UserDevice.device_id == Device.id
        ).where(
            and_(
                Device.family_id == family_id,
                Item.tag_uid == tag_uid,
                Item.is_active == True
            )
        ).order_by(Item.created_at.desc(), Item.id.desc())

        if exclude_item_id is not None:
            stmt = stmt.where(Item.id != exclude_item_id)

        return self.db.execute(stmt).scalars().first()

    def get_used_tag_uids_by_user_device_id(self, user_device_id: int) -> Set[str]:
        """사용자 디바이스에서 사용 중인 태그 UID 집합 반환"""
        stmt = select(Item.tag_uid).where(
            and_(
                Item.user_device_id == user_device_id,
                Item.is_active == True
            )
        )
        result = self.db.execute(stmt).scalars().all()
        return set(result)

    def exists_by_user_device_id(self, user_device_id: int) -> bool:
        """사용자 디바이스에 아이템 존재 여부 확인"""
        stmt = select(Item.id).where(Item.user_device_id == user_device_id).limit(1)
        return self.db.execute(stmt).scalar_one_or_none() is not None

    def create(self, user_device_id: int, name: str, tag_uid: str) -> Item:
        """새 아이템 생성"""
        item = Item(
            user_device_id=user_device_id,
            name=name,
            tag_uid=tag_uid,
            is_active=True
        )
        self.db.add(item)
        self.db.flush()
        return item

    def update(self, item: Item, name: Optional[str] = None, tag_uid: Optional[str] = None) -> Item:
        """아이템 정보 업데이트 (선택적 필드만 수정)"""
        if name is not None:
            item.name = name
        if tag_uid is not None:
            item.tag_uid = tag_uid
        self.db.flush()
        return item

    def soft_delete(self, item: Item) -> Item:
        """아이템 비활성화 (소프트 삭제)"""
        item.is_active = False
        self.db.flush()
        return item