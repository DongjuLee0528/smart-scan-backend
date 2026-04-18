"""
가상 태그 데이터 접근 계층

사용자가 생성한 가상 태그(Virtual Tag)의 데이터베이스 작업을 담당하는 리포지토리입니다.
가상 태그는 실제 물리적 RFID 태그와 연결되기 전 단계의 태그 정보를 관리합니다.

데이터 관리:
- 가상 태그 생성, 수정, 삭제
- 태그 UID를 통한 물리적 태그와의 매핑
- 사용자별 태그 소유권 관리
- 태그 메타데이터 (이름, 설명, 색상 등) 저장

비즈니스 규칙:
- 태그 UID는 전체 시스템에서 고유해야 함
- 사용자는 본인이 생성한 태그만 관리 가능
- 가족 구성원은 서로의 태그 조회 가능 (읽기 전용)
- 태그 삭제 시 연관된 아이템 존재 여부 확인 필요

주요 쿼리 패턴:
- 태그 UID로 태그 조회 (물리적 태그 연결 시 사용)
- 사용자별 태그 목록 조회 (소유권 기반)
- 가족별 태그 목록 조회 (공유 접근)
- 태그 상태별 필터링 (활성/비활성)
"""

from typing import Optional

from sqlalchemy.orm import Session, joinedload

from backend.models.tag import Tag


class TagRepository:
    """
    가상 태그 데이터 접근 클래스

    태그 테이블에 대한 CRUD 작업과 태그 관리 비즈니스 로직을 제공합니다.
    """
    def __init__(self, db: Session):
        """데이터베이스 세션 주입"""
        self.db = db

    def find_by_id(self, tag_id: int) -> Optional[Tag]:
        """태그 ID로 조회"""
        return self.db.query(Tag).filter(Tag.id == tag_id).first()

    def find_by_tag_uid(self, tag_uid: str) -> Optional[Tag]:
        """태그 UID로 조회 (물리적 태그 연결 시 사용)"""
        return self.db.query(Tag).filter(Tag.tag_uid == tag_uid).first()

    def find_active_by_family_id(self, family_id: int) -> list[Tag]:
        """가족의 활성 태그 목록 조회 (소유자 정보 포함)"""
        return self.db.query(Tag).options(
            joinedload(Tag.owner)
        ).filter(
            Tag.family_id == family_id,
            Tag.is_active.is_(True)
        ).order_by(Tag.created_at.desc()).all()

    def find_active_by_family_id_and_owner_user_id(self, family_id: int, owner_user_id: int) -> list[Tag]:
        """특정 소유자의 활성 태그 목록 조회"""
        return self.db.query(Tag).options(
            joinedload(Tag.owner)
        ).filter(
            Tag.family_id == family_id,
            Tag.owner_user_id == owner_user_id,
            Tag.is_active.is_(True)
        ).order_by(Tag.created_at.desc()).all()

    def create(
        self,
        tag_uid: str,
        name: str,
        family_id: int,
        owner_user_id: int,
        device_id: int
    ) -> Tag:
        """새 가상 태그 생성"""
        tag = Tag(
            tag_uid=tag_uid,
            name=name,
            family_id=family_id,
            owner_user_id=owner_user_id,
            device_id=device_id,
            is_active=True
        )
        self.db.add(tag)
        self.db.flush()
        return tag

    def update(
        self,
        tag: Tag,
        name: str | None = None,
        owner_user_id: int | None = None,
        device_id: int | None = None,
        is_active: bool | None = None
    ) -> Tag:
        """태그 정보 업데이트 (선택적 필드만 수정)"""
        if name is not None:
            tag.name = name
        if owner_user_id is not None:
            tag.owner_user_id = owner_user_id
        if device_id is not None:
            tag.device_id = device_id
        if is_active is not None:
            tag.is_active = is_active
        self.db.flush()
        return tag

    def soft_delete(self, tag: Tag) -> Tag:
        """태그 비활성화 (소프트 삭제)"""
        tag.is_active = False
        self.db.flush()
        return tag