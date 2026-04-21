from sqlalchemy.orm import Session

from backend.common.exceptions import BadRequestException, ForbiddenException, NotFoundException
from backend.common.validator import validate_positive_int
from backend.repositories.item_repository import ItemRepository
from backend.repositories.master_tag_repository import MasterTagRepository
from backend.repositories.user_device_repository import UserDeviceRepository
from backend.schemas.item_schema import ItemListResponse, ItemResponse


class ItemService:
    """
    스마트 태그 연결 아이템 관리 서비스

    사용자가 태그와 연결할 실제 물건(아이템)의 등록과 관리를 담당한다.
    아이템은 마스터 태그(물리적 태그)와 연결되며, 라벨을 통해 분류될 수 있다.

    설계 의도:
    - 가족 공유 아이템: 가족 구성원이면 누구나 아이템 조회 가능
    - 태그-아이템 1:1 매칭: 하나의 마스터 태그에는 하나의 활성 아이템만 연결
    - 라벨 기반 분류: 아이템을 카테고리별로 관리하여 사용자 편의성 제공
    - 가족 디바이스 종속: 가족에 등록된 디바이스를 통해서만 아이템 관리 가능
    """
    def __init__(self, db: Session):
        """아이템 관리에 필요한 리포지토리 초기화"""
        self.db = db
        self.item_repository = ItemRepository(db)
        self.master_tag_repository = MasterTagRepository(db)
        self.user_device_repository = UserDeviceRepository(db)

    def get_items(self, user_id: int) -> ItemListResponse:
        """
        가족에 등록된 모든 아이템 목록 조회

        사용자가 속한 가족의 디바이스에 등록된 모든 활성 아이템을 라벨 정보와 함께 반환한다.
        다른 가족 구성원이 등록한 아이템도 조회 가능하여 가족 공유 사용을 지원한다.
        """
        validate_positive_int(user_id, "user_id")
        user_device = self._get_family_registered_user_device(user_id)

        items_with_labels = self.item_repository.get_active_items_with_label_by_user_device_id(user_device.id)

        item_responses = []
        for item, label_id in items_with_labels:
            item_response = ItemResponse(
                id=item.id,
                name=item.name,
                label_id=label_id,
                created_at=item.created_at,
                updated_at=item.updated_at,
                is_active=item.is_active,
                is_pending=item.is_pending
            )
            item_responses.append(item_response)

        return ItemListResponse(
            items=item_responses,
            total_count=len(item_responses)
        )

    def add_item(self, user_id: int, name: str, label_id: int) -> ItemResponse:
        """
        새로운 아이템 등록

        사용자가 지정한 라벨에 대응하는 마스터 태그를 사용하여 새로운 아이템을 등록한다.
        동일한 태그 UID로 다른 아이템이 이미 등록되어 있으면 오류를 발생시킨다.
        """
        validate_positive_int(user_id, "user_id")
        user_device = self._get_family_registered_user_device(user_id)

        master_tag = self.master_tag_repository.get_by_label_id_and_device_id(
            label_id, user_device.device_id
        )
        if not master_tag:
            raise NotFoundException("해당 라벨을 찾을 수 없습니다")

        self._ensure_family_tag_uid_available(
            family_id=user_device.device.family_id,
            tag_uid=master_tag.tag_uid
        )

        try:
            item = self.item_repository.create(
                user_device_id=user_device.id,
                name=name,
                tag_uid=master_tag.tag_uid
            )
            self.db.commit()
            self.db.refresh(item)
            return ItemResponse(
                id=item.id,
                name=item.name,
                label_id=label_id,
                created_at=item.created_at,
                updated_at=item.updated_at,
                is_active=item.is_active,
                is_pending=item.is_pending
            )
        except Exception:
            self.db.rollback()
            raise

    def update_item(self, item_id: int, user_id: int, name: str = None, label_id: int = None) -> ItemResponse:
        """
        아이템 정보 수정

        아이템의 이름이나 라벨을 수정한다.
        라벨 변경 시 다른 마스터 태그로 연결되며, 새로운 태그 UID의 사용 가능 여부를 검사한다.
        본인이 등록한 아이템만 수정 가능하다.
        """
        validate_positive_int(user_id, "user_id")
        user_device = self._get_family_registered_user_device(user_id)

        item = self.item_repository.get_by_id(item_id)
        if not item or not item.is_active:
            raise NotFoundException("물품을 찾을 수 없습니다")

        if item.user_device_id != user_device.id:
            raise ForbiddenException("본인 소유 물품이 아닙니다")

        if item.is_pending or item.tag_uid is None:
            raise BadRequestException("라벨 연결 대기 중인 물품은 먼저 라벨을 연결해야 수정할 수 있습니다")

        new_tag_uid = None
        current_master_tag = self.master_tag_repository.get_by_tag_uid_and_device_id(item.tag_uid, user_device.device_id)
        if not current_master_tag:
            raise NotFoundException("연결된 라벨 정보를 찾을 수 없습니다")
        response_label_id = current_master_tag.label_id

        if label_id is not None:
            master_tag = self.master_tag_repository.get_by_label_id_and_device_id(
                label_id, user_device.device_id
            )
            if not master_tag:
                raise NotFoundException("해당 라벨을 찾을 수 없습니다")

            if master_tag.tag_uid != item.tag_uid:
                self._ensure_family_tag_uid_available(
                    family_id=user_device.device.family_id,
                    tag_uid=master_tag.tag_uid,
                    exclude_item_id=item.id
                )

                new_tag_uid = master_tag.tag_uid
                response_label_id = label_id

        try:
            updated_item = self.item_repository.update(
                item=item,
                name=name,
                tag_uid=new_tag_uid
            )
            self.db.commit()
            self.db.refresh(updated_item)
            return ItemResponse(
                id=updated_item.id,
                name=updated_item.name,
                label_id=response_label_id,
                created_at=updated_item.created_at,
                updated_at=updated_item.updated_at,
                is_active=updated_item.is_active,
                is_pending=updated_item.is_pending
            )
        except Exception:
            self.db.rollback()
            raise

    def delete_item(self, item_id: int, user_id: int) -> bool:
        """
        아이템 삭제 (연삭제)

        아이템을 비활성 상태로 만들어 논리적으로 삭제한다.
        본인이 등록한 아이템만 삭제 가능하다.
        """
        validate_positive_int(user_id, "user_id")
        user_device = self._get_family_registered_user_device(user_id)

        item = self.item_repository.get_by_id(item_id)
        if not item or not item.is_active:
            raise NotFoundException("물품을 찾을 수 없습니다")

        if item.user_device_id != user_device.id:
            raise ForbiddenException("본인 소유 물품이 아닙니다")

        try:
            self.item_repository.soft_delete(item)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def bind_item(self, item_id: int, user_id: int, label_id: int) -> ItemResponse:
        """
        Pending 아이템에 라벨(마스터 태그)을 연결하여 활성 아이템으로 전환

        챗봇에서 이름만 추가된 is_pending=True 아이템을 웹에서 라벨과 연결한다.
        """
        validate_positive_int(user_id, "user_id")
        user_device = self._get_family_registered_user_device(user_id)

        item = self.item_repository.get_by_id(item_id)
        if not item or not item.is_active:
            raise NotFoundException("물품을 찾을 수 없습니다")
        if item.user_device_id != user_device.id:
            raise ForbiddenException("본인 소유 물품이 아닙니다")
        if not item.is_pending:
            raise BadRequestException("이미 라벨이 연결된 물품입니다")

        master_tag = self.master_tag_repository.get_by_label_id_and_device_id(
            label_id, user_device.device_id
        )
        if not master_tag:
            raise NotFoundException("해당 라벨을 찾을 수 없습니다")

        self._ensure_family_tag_uid_available(
            family_id=user_device.device.family_id,
            tag_uid=master_tag.tag_uid,
            exclude_item_id=item.id
        )

        try:
            updated = self.item_repository.bind_tag(item=item, tag_uid=master_tag.tag_uid)
            self.db.commit()
            self.db.refresh(updated)
            return ItemResponse(
                id=updated.id,
                name=updated.name,
                label_id=label_id,
                created_at=updated.created_at,
                updated_at=updated.updated_at,
                is_active=updated.is_active,
                is_pending=updated.is_pending
            )
        except Exception:
            self.db.rollback()
            raise

    # ---------- Chatbot-facing methods (kakao_user_id 기반) ----------
    def chatbot_list_items(self, kakao_user_id: str) -> ItemListResponse:
        """챗봇: 활성 아이템 목록 (pending 포함, label_id 미할당일 수 있음)."""
        user_device = self._get_kakao_user_device(kakao_user_id)
        items_with_labels = self.item_repository.get_active_items_with_label_by_user_device_id(user_device.id)
        responses = [
            ItemResponse(
                id=item.id,
                name=item.name,
                label_id=label_id,
                created_at=item.created_at,
                updated_at=item.updated_at,
                is_active=item.is_active,
                is_pending=item.is_pending,
            )
            for item, label_id in items_with_labels
        ]
        return ItemListResponse(items=responses, total_count=len(responses))

    def chatbot_add_pending_item(self, kakao_user_id: str, name: str) -> ItemResponse:
        """챗봇: 이름만으로 pending 아이템 추가."""
        user_device = self._get_kakao_user_device(kakao_user_id)
        try:
            item = self.item_repository.create_pending(
                user_device_id=user_device.id,
                name=name,
            )
            self.db.commit()
            self.db.refresh(item)
            return ItemResponse(
                id=item.id,
                name=item.name,
                label_id=None,
                created_at=item.created_at,
                updated_at=item.updated_at,
                is_active=item.is_active,
                is_pending=item.is_pending,
            )
        except Exception:
            self.db.rollback()
            raise

    def chatbot_delete_by_name(self, kakao_user_id: str, name: str) -> int:
        """챗봇: 이름으로 아이템을 찾아 soft-delete. 반환: 삭제된 수 (0 or 1)."""
        user_device = self._get_kakao_user_device(kakao_user_id)
        item = self.item_repository.get_active_by_user_device_and_name(user_device.id, name)
        if not item:
            return 0
        try:
            self.item_repository.soft_delete(item)
            self.db.commit()
            return 1
        except Exception:
            self.db.rollback()
            raise

    def chatbot_unlink_device(self, kakao_user_id: str) -> int:
        """챗봇: 해당 유저의 모든 활성 아이템을 일괄 soft-delete. 반환: 삭제 수."""
        user_device = self._get_kakao_user_device(kakao_user_id)
        items = self.item_repository.get_all_active_by_user_device_id(user_device.id)
        count = 0
        try:
            for item in items:
                self.item_repository.soft_delete(item)
                count += 1
            self.db.commit()
            return count
        except Exception:
            self.db.rollback()
            raise

    def _get_kakao_user_device(self, kakao_user_id: str):
        """카카오 사용자 ID로 가족 등록 디바이스 조회 (챗봇 엔드포인트 전용)."""
        if not kakao_user_id or not kakao_user_id.strip():
            raise BadRequestException("kakao_user_id가 비어 있습니다")
        user_device = self.user_device_repository.get_by_kakao_user_id(kakao_user_id.strip())
        if not user_device:
            raise NotFoundException("연결된 기기를 찾을 수 없습니다")
        if not user_device.device or user_device.device.family_id is None:
            raise BadRequestException("사용자 기기가 가족에 등록되어 있지 않습니다")
        return user_device

    def _get_family_registered_user_device(self, user_id: int):
        """사용자의 가족 등록 디바이스 조회 (아이템 관리 전 필수 확인)"""
        user_device = self.user_device_repository.find_by_user_id(user_id)
        if not user_device:
            raise NotFoundException("사용자 기기를 찾을 수 없습니다")
        if not user_device.device or user_device.device.family_id is None:
            raise BadRequestException("사용자 기기가 가족에 등록되어 있지 않습니다")
        return user_device

    def _ensure_family_tag_uid_available(
        self,
        family_id: int,
        tag_uid: str,
        exclude_item_id: int | None = None
    ) -> None:
        """
        가족 내 태그 UID 중복 사용 방지 검증

        동일한 가족에서 같은 태그 UID를 사용하는 다른 아이템이 있는지 확인한다.
        exclude_item_id를 사용하여 수정 시 자기 자신은 제외할 수 있다.
        """
        existing_item = self.item_repository.get_by_family_id_and_tag_uid(
            family_id=family_id,
            tag_uid=tag_uid,
            exclude_item_id=exclude_item_id
        )
        if existing_item:
            raise BadRequestException("이미 가족 내에서 사용 중인 라벨입니다")
