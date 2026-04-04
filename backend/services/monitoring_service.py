from sqlalchemy.orm import Session

from backend.common.exceptions import BadRequestException, ForbiddenException, NotFoundException
from backend.common.validator import validate_kakao_user_id, validate_positive_int
from backend.repositories.family_member_repository import FamilyMemberRepository
from backend.repositories.family_repository import FamilyRepository
from backend.repositories.item_repository import ItemRepository
from backend.repositories.scan_log_repository import ScanLogRepository
from backend.repositories.tag_repository import TagRepository
from backend.repositories.user_device_repository import UserDeviceRepository
from backend.repositories.user_repository import UserRepository
from backend.schemas.monitoring_schema import (
    DashboardSummaryResponse,
    MemberSummaryResponse,
    MemberTagStatusListResponse,
    MonitoringDashboardResponse,
    MyTagStatusListResponse,
    TagCurrentStatus,
    TagStatusResponse,
)


class MonitoringService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repository = UserRepository(db)
        self.family_repository = FamilyRepository(db)
        self.family_member_repository = FamilyMemberRepository(db)
        self.tag_repository = TagRepository(db)
        self.user_device_repository = UserDeviceRepository(db)
        self.item_repository = ItemRepository(db)
        self.scan_log_repository = ScanLogRepository(db)

    def get_dashboard(self, kakao_user_id: str) -> MonitoringDashboardResponse:
        actor, requester_member, family = self._get_actor_context(kakao_user_id)
        family_members = self.family_member_repository.find_all_by_family_id(family.id)
        tag_statuses = self._build_family_tag_statuses(family.id, family_members)

        member_summaries = []
        for member in family_members:
            member_tags = [tag for tag in tag_statuses if tag.owner_user_id == member.user_id]
            member_summaries.append(
                MemberSummaryResponse(
                    member_id=member.id,
                    user_id=member.user_id,
                    name=member.user.name if member.user else None,
                    email=member.user.email if member.user else None,
                    role=member.role,
                    tag_count=len(member_tags),
                    found_count=self._count_status(member_tags, TagCurrentStatus.FOUND),
                    lost_count=self._count_status(member_tags, TagCurrentStatus.LOST),
                    registered_count=self._count_status(member_tags, TagCurrentStatus.REGISTERED),
                )
            )

        return MonitoringDashboardResponse(
            family_id=family.id,
            family_name=family.family_name,
            requester_member_id=requester_member.id,
            requester_role=requester_member.role,
            summary=DashboardSummaryResponse(
                total_members=len(family_members),
                total_tags=len(tag_statuses),
                found_count=self._count_status(tag_statuses, TagCurrentStatus.FOUND),
                lost_count=self._count_status(tag_statuses, TagCurrentStatus.LOST),
                registered_count=self._count_status(tag_statuses, TagCurrentStatus.REGISTERED),
            ),
            members=member_summaries
        )

    def get_member_tags(self, kakao_user_id: str, member_id: int) -> MemberTagStatusListResponse:
        validate_kakao_user_id(kakao_user_id)
        validate_positive_int(member_id, "member_id")

        _, _, family = self._get_actor_context(kakao_user_id)
        target_member = self.family_member_repository.find_by_id(member_id)
        if not target_member:
            raise NotFoundException("Family member not found")

        if target_member.family_id != family.id:
            raise ForbiddenException("Family member is not accessible in this family")

        family_members = self.family_member_repository.find_all_by_family_id(family.id)
        tag_statuses = self._build_family_tag_statuses(family.id, family_members)
        filtered_tags = [tag for tag in tag_statuses if tag.owner_user_id == target_member.user_id]

        return MemberTagStatusListResponse(
            family_id=family.id,
            family_name=family.family_name,
            member_id=target_member.id,
            user_id=target_member.user_id,
            member_name=target_member.user.name if target_member.user else None,
            role=target_member.role,
            tags=filtered_tags,
            total_count=len(filtered_tags)
        )

    def get_my_tag_statuses(self, kakao_user_id: str) -> MyTagStatusListResponse:
        actor, family_member, family = self._get_actor_context(kakao_user_id)
        family_members = self.family_member_repository.find_all_by_family_id(family.id)
        tag_statuses = self._build_family_tag_statuses(family.id, family_members)
        my_tags = [tag for tag in tag_statuses if tag.owner_user_id == actor.id]

        return MyTagStatusListResponse(
            family_id=family.id,
            family_name=family.family_name,
            member_id=family_member.id,
            tags=my_tags,
            total_count=len(my_tags)
        )

    def _get_actor_context(self, kakao_user_id: str):
        validate_kakao_user_id(kakao_user_id)

        actor = self.user_repository.find_by_kakao_user_id(kakao_user_id.strip())
        if not actor:
            raise NotFoundException("User not found")

        family_member = self.family_member_repository.find_by_user_id(actor.id)
        if not family_member:
            raise BadRequestException("User is not assigned to a family")

        family = self.family_repository.find_by_id(family_member.family_id)
        if not family:
            raise NotFoundException("Family not found")

        return actor, family_member, family

    def _build_family_tag_statuses(self, family_id: int, family_members) -> list[TagStatusResponse]:
        tags = self.tag_repository.find_active_by_family_id(family_id)
        member_by_user_id = {member.user_id: member for member in family_members}

        user_ids = [member.user_id for member in family_members]
        user_devices = self.user_device_repository.find_all_by_user_ids(user_ids)
        user_device_ids = [user_device.id for user_device in user_devices]

        items = self.item_repository.get_active_items_by_user_device_ids(user_device_ids)
        item_by_tag_uid = {}
        for item in items:
            if item.tag_uid not in item_by_tag_uid:
                item_by_tag_uid[item.tag_uid] = item

        latest_logs_by_item_id = self.scan_log_repository.find_latest_by_item_ids(
            [item.id for item in items]
        )

        tag_statuses = []
        for tag in tags:
            owner_member = member_by_user_id.get(tag.owner_user_id)
            item = item_by_tag_uid.get(tag.tag_uid)
            latest_log = latest_logs_by_item_id.get(item.id) if item else None
            status = self._resolve_tag_status(latest_log.status if latest_log else None)

            tag_statuses.append(
                TagStatusResponse(
                    tag_id=tag.id,
                    tag_uid=tag.tag_uid,
                    name=tag.name,
                    owner_user_id=tag.owner_user_id,
                    owner_member_id=owner_member.id if owner_member else None,
                    owner_name=tag.owner.name if tag.owner else None,
                    status=status,
                    is_active=tag.is_active,
                    item_id=item.id if item else None,
                    item_name=item.name if item else None,
                    last_scanned_at=latest_log.scanned_at if latest_log else None,
                    created_at=tag.created_at,
                    updated_at=tag.updated_at
                )
            )

        return tag_statuses

    @staticmethod
    def _resolve_tag_status(raw_status: str | None) -> TagCurrentStatus:
        if raw_status == TagCurrentStatus.FOUND.value:
            return TagCurrentStatus.FOUND
        if raw_status == TagCurrentStatus.LOST.value:
            return TagCurrentStatus.LOST
        return TagCurrentStatus.REGISTERED

    @staticmethod
    def _count_status(tags: list[TagStatusResponse], status: TagCurrentStatus) -> int:
        return sum(1 for tag in tags if tag.status == status)
