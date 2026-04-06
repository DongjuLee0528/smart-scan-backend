from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from backend.common.config import settings
from backend.common.exceptions import BadRequestException, ForbiddenException, NotFoundException
from backend.common.validator import validate_positive_int
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
        self.monitoring_found_window_minutes = settings.MONITORING_FOUND_WINDOW_MINUTES

    def get_dashboard(self, user_id: int) -> MonitoringDashboardResponse:
        actor, requester_member, family = self._get_actor_context(user_id)
        family_members, tag_statuses = self._get_family_members_and_tag_statuses(family.id)

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

    def get_member_tags(self, user_id: int, member_id: int) -> MemberTagStatusListResponse:
        validate_positive_int(user_id, "user_id")
        validate_positive_int(member_id, "member_id")

        _, _, family = self._get_actor_context(user_id)
        target_member = self.family_member_repository.find_by_id(member_id)
        if not target_member:
            raise NotFoundException("Family member not found")

        if target_member.family_id != family.id:
            raise ForbiddenException("Family member is not accessible in this family")

        _, tag_statuses = self._get_family_members_and_tag_statuses(family.id)
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

    def get_my_tag_statuses(self, user_id: int) -> MyTagStatusListResponse:
        validate_positive_int(user_id, "user_id")
        actor, family_member, family = self._get_actor_context(user_id)
        _, tag_statuses = self._get_family_members_and_tag_statuses(family.id)
        my_tags = [tag for tag in tag_statuses if tag.owner_user_id == actor.id]

        return MyTagStatusListResponse(
            family_id=family.id,
            family_name=family.family_name,
            member_id=family_member.id,
            tags=my_tags,
            total_count=len(my_tags)
        )

    def _get_actor_context(self, user_id: int):
        actor = self.user_repository.find_by_id(user_id)
        if not actor:
            raise NotFoundException("User not found")

        family_member = self.family_member_repository.find_by_user_id(actor.id)
        if not family_member:
            raise BadRequestException("User is not assigned to a family")

        family = self.family_repository.find_by_id(family_member.family_id)
        if not family:
            raise NotFoundException("Family not found")

        return actor, family_member, family

    def _get_family_members_and_tag_statuses(self, family_id: int):
        family_members = self.family_member_repository.find_all_by_family_id(family_id)
        tag_statuses = self._build_family_tag_statuses(family_id, family_members)
        return family_members, tag_statuses

    def _build_family_tag_statuses(self, family_id: int, family_members) -> list[TagStatusResponse]:
        tags = self.tag_repository.find_active_by_family_id(family_id)
        member_by_user_id = {member.user_id: member for member in family_members}
        user_device_by_id = self._get_family_user_device_map(family_id, family_members)
        item_by_owner_and_tag_uid = self._get_item_lookup_by_owner_and_tag_uid(user_device_by_id)
        latest_logs_by_item_id = self.scan_log_repository.find_latest_by_item_ids(
            [item.id for item in item_by_owner_and_tag_uid.values()]
        )
        found_window_started_at = self._get_found_window_started_at()

        tag_statuses = []
        for tag in tags:
            owner_member = member_by_user_id.get(tag.owner_user_id)
            item = item_by_owner_and_tag_uid.get((tag.owner_user_id, tag.tag_uid))
            latest_log = latest_logs_by_item_id.get(item.id) if item else None
            tag_statuses.append(
                self._build_tag_status_response(
                    tag=tag,
                    owner_member=owner_member,
                    item=item,
                    latest_log=latest_log,
                    user_device_by_id=user_device_by_id,
                    found_window_started_at=found_window_started_at
                )
            )

        return tag_statuses

    def _get_family_user_device_map(self, family_id: int, family_members) -> dict[int, object]:
        user_ids = [member.user_id for member in family_members]
        family_user_devices = [
            user_device
            for user_device in self.user_device_repository.find_all_by_user_ids(user_ids)
            if user_device.device and user_device.device.family_id == family_id
        ]
        return {user_device.id: user_device for user_device in family_user_devices}

    def _get_item_lookup_by_owner_and_tag_uid(self, user_device_by_id: dict[int, object]) -> dict[tuple[int, str], object]:
        items = self.item_repository.get_active_items_by_user_device_ids(list(user_device_by_id.keys()))
        item_by_owner_and_tag_uid = {}

        for item in items:
            owner_user_device = user_device_by_id.get(item.user_device_id)
            if not owner_user_device:
                continue

            lookup_key = (owner_user_device.user_id, item.tag_uid)
            if lookup_key not in item_by_owner_and_tag_uid:
                item_by_owner_and_tag_uid[lookup_key] = item

        return item_by_owner_and_tag_uid

    def _build_tag_status_response(
        self,
        tag,
        owner_member,
        item,
        latest_log,
        user_device_by_id: dict[int, object],
        found_window_started_at: datetime
    ) -> TagStatusResponse:
        last_seen_at = self._normalize_datetime(latest_log.scanned_at) if latest_log else None
        latest_user_device = user_device_by_id.get(latest_log.user_device_id) if latest_log else None
        status = self._resolve_tag_status(item is not None, last_seen_at, found_window_started_at)

        return TagStatusResponse(
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
            device_id=latest_user_device.device_id if latest_user_device else None,
            last_seen_at=last_seen_at,
            last_scanned_at=last_seen_at,
            created_at=tag.created_at,
            updated_at=tag.updated_at
        )

    def _get_found_window_started_at(self) -> datetime:
        return datetime.now(timezone.utc) - timedelta(
            minutes=self.monitoring_found_window_minutes
        )

    @staticmethod
    def _resolve_tag_status(
        has_linked_item: bool,
        last_seen_at: datetime | None,
        found_window_started_at: datetime
    ) -> TagCurrentStatus:
        if not has_linked_item or last_seen_at is None:
            return TagCurrentStatus.REGISTERED
        if last_seen_at >= found_window_started_at:
            return TagCurrentStatus.FOUND
        return TagCurrentStatus.LOST

    @staticmethod
    def _normalize_datetime(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    @staticmethod
    def _count_status(tags: list[TagStatusResponse], status: TagCurrentStatus) -> int:
        return sum(1 for tag in tags if tag.status == status)
