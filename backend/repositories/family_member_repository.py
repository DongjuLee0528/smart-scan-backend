"""
가족 구성원 데이터 접근 계층

Smart Scan 시스템에서 가족 구성원 정보를 관리하는 레포지토리입니다.
가족과 사용자 간의 연결 정보와 역할을 관리합니다.

데이터 관리:
- 가족 구성원 추가/제거
- 구성원 역할 및 권한 관리
- 가족별 구성원 목록 조회

비즈니스 규칙:
- owner: 가족 소유자, 전체 권한 보유
- member: 일반 가족 구성원, 제한적 권한
- 가족당 한 명의 소유자만 존재 가능

주요 사용 케이스:
- 사용자 회원가입 시 가족 소유자로 등록
- 가족 초대 시 새 구성원 추가
- 가족 단위 데이터 접근 권한 검증
"""

from typing import Optional

from sqlalchemy.orm import Session, joinedload

from backend.models.family_member import FamilyMember


class FamilyMemberRepository:
    """
    가족 구성원 데이터 접근 계층

    가족 구성원(FamilyMember) 모델의 CRUD 연산을 담당하는 리포지토리.
    가족과 사용자 간의 연결 정보와 역할 관리 기능을 제공한다.

    주요 책임:
    - 가족 구성원 엔티티의 데이터베이스 연산
    - 사용자와 가족 간의 매핑 관리
    - 가족 내 역할 및 권한 관리
    """
    def __init__(self, db: Session):
        """데이터베이스 세션 주입"""
        self.db = db

    def find_by_user_id(self, user_id: int) -> Optional[FamilyMember]:
        """사용자 ID로 가족 구성원 정보 조회"""
        return self.db.query(FamilyMember).filter(FamilyMember.user_id == user_id).first()

    def find_by_id(self, family_member_id: int) -> Optional[FamilyMember]:
        """가족 구성원 ID로 조회 (사용자 정보 포함)"""
        return self.db.query(FamilyMember).options(
            joinedload(FamilyMember.user)
        ).filter(FamilyMember.id == family_member_id).first()

    def find_all_by_family_id(self, family_id: int) -> list[FamilyMember]:
        """가족의 모든 구성원 목록 조회 (사용자 정보 포함)"""
        return self.db.query(FamilyMember).options(
            joinedload(FamilyMember.user)
        ).filter(
            FamilyMember.family_id == family_id
        ).order_by(FamilyMember.created_at.asc(), FamilyMember.id.asc()).all()

    def find_by_family_id_and_user_id(self, family_id: int, user_id: int) -> Optional[FamilyMember]:
        """가족 ID와 사용자 ID로 구성원 정보 조회"""
        return self.db.query(FamilyMember).filter(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == user_id
        ).first()

    def exists_by_user_id(self, user_id: int) -> bool:
        """사용자의 가족 소속 여부 확인"""
        return self.find_by_user_id(user_id) is not None

    def create(self, family_id: int, user_id: int, role: str) -> FamilyMember:
        """새 가족 구성원 생성"""
        family_member = FamilyMember(family_id=family_id, user_id=user_id, role=role)
        self.db.add(family_member)
        self.db.flush()
        return family_member

    def delete(self, family_member: FamilyMember) -> None:
        """가족 구성원 삭제"""
        self.db.delete(family_member)
        self.db.flush()
