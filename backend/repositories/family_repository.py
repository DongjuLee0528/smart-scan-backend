"""
가족 그룹 데이터 접근 계층

SmartScan 시스템의 가족 그룹 데이터를 관리하는 레포지토리입니다.
가족 단위로 디바이스와 소지품을 공유하는 SmartScan의 핵심 개념입니다.

데이터 관리:
- 가족 그룹 생성 및 메타데이터 관리
- 가족 소유자(Owner) 및 구성원 권한 관리
- 가족 이름, 설명, 설정 정보 저장

비즈니스 규칙:
- 가족 소유자만 가족 삭제 및 주요 설정 변경 가능
- 가족 삭제 시 모든 연관 데이터(구성원, 디바이스, 아이템) 연쇄 삭제
- 가족 이름은 소유자 내에서 고유할 필요 없음

주요 사용 케이스:
- 사용자 회원가입 시 기본 가족 생성
- 가족 구성원 초대 및 구성원 권한 검증
- 가족 단위 데이터 접근 제어
"""

from sqlalchemy.orm import Session
from backend.models.family import Family


class FamilyRepository:
    """
    가족 그룹 데이터 접근 클래스

    가족 테이블에 대한 CRUD 작업과 가족 관리 비즈니스 로직을 제공합니다.
    """
    def __init__(self, db: Session):
        self.db = db

    def create(self, family_name: str, owner_user_id: int) -> Family:
        """
        새로운 가족 그룹 생성

        사용자 회원가입 시 또는 수동으로 새 가족 그룹을 생성합니다.
        생성자가 자동으로 가족 소유자가 됩니다.
        """
        family = Family(family_name=family_name, owner_user_id=owner_user_id)
        self.db.add(family)
        self.db.flush()
        return family

    def find_by_id(self, family_id: int) -> Family | None:
        """
        가족 ID로 가족 그룹 조회

        Args:
            family_id: 조회할 가족의 고유 ID

        Returns:
            Family | None: 일치하는 가족 그룹 또는 None
        """
        return self.db.query(Family).filter(Family.id == family_id).first()
