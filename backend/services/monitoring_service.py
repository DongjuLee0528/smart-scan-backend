from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.common.datetime_utils import normalize_datetime
from backend.common.exceptions import BadRequestException, ForbiddenException, NotFoundException
from backend.common.service_base import ServiceBase
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
from backend.schemas.scan_log_schema import ScanStatus


class MonitoringService(ServiceBase):
    def __init__(self, db: Session):
        super().__init__(db)
        self.tag_repository = TagRepository(db)
        self.user_device_repository = UserDeviceRepository(db)
        self.item_repository = ItemRepository(db)
        self.scan_log_repository = ScanLogRepository(db)

    def get_dashboard(self, user_id: int) -> MonitoringDashboardResponse:
        actor, requester_member, family = self._get_actor_context(user_id)
        family_members, tag_statuses = self._get_family_tag_monitoring_data(family.id)

        member_summaries = self._build_member_summaries(family_members, tag_statuses)
        dashboard_summary = self._build_dashboard_summary(family_members, tag_statuses)

        return MonitoringDashboardResponse(
            family_id=family.id,
            family_name=family.family_name,
            requester_member_id=requester_member.id,
            requester_role=requester_member.role,
            summary=dashboard_summary,
            members=member_summaries
        )

    def get_member_tags(self, user_id: int, member_id: int) -> MemberTagStatusListResponse:
        validate_positive_int(user_id, "user_id")
        validate_positive_int(member_id, "member_id")

        _, _, family = self._get_actor_context(user_id)
        target_member = self._validate_member_access(member_id, family.id)

        _, tag_statuses = self._get_family_tag_monitoring_data(family.id)
        member_tags = self._filter_tags_by_owner(tag_statuses, target_member.user_id)

        return MemberTagStatusListResponse(
            family_id=family.id,
            family_name=family.family_name,
            member_id=target_member.id,
            user_id=target_member.user_id,
            member_name=target_member.user.name if target_member.user else None,
            role=target_member.role,
            tags=member_tags,
            total_count=len(member_tags)
        )

    def get_my_tag_statuses(self, user_id: int) -> MyTagStatusListResponse:
        validate_positive_int(user_id, "user_id")
        actor, family_member, family = self._get_actor_context(user_id)

        _, tag_statuses = self._get_family_tag_monitoring_data(family.id)
        my_tags = self._filter_tags_by_owner(tag_statuses, user_id)

        return MyTagStatusListResponse(
            family_id=family.id,
            family_name=family.family_name,
            member_id=family_member.id,
            tags=my_tags,
            total_count=len(my_tags)
        )

    def _validate_member_access(self, member_id: int, family_id: int):
        target_member = self.family_member_repository.find_by_id(member_id)
        if not target_member:
            raise NotFoundException("Family member not found")

        if target_member.family_id != family_id:
            raise ForbiddenException("Family member is not accessible in this family")

        return target_member

    def _get_family_tag_monitoring_data(self, family_id: int):
        family_members = self.family_member_repository.find_all_by_family_id(family_id)
        tag_statuses = self._build_family_tag_statuses(family_id, family_members)
        return family_members, tag_statuses

    def _build_member_summaries(self, family_members, tag_statuses) -> list[MemberSummaryResponse]:
        member_summaries = []
        for member in family_members:
            member_tags = self._filter_tags_by_owner(tag_statuses, member.user_id)
            member_summaries.append(
                MemberSummaryResponse(
                    member_id=member.id,
                    user_id=member.user_id,
                    name=member.user.name if member.user else None,
                    email=member.user.email if member.user else None,
                    role=member.role,
                    tag_count=len(member_tags),
                    found_count=self._count_tags_by_status(member_tags, TagCurrentStatus.FOUND),
                    lost_count=self._count_tags_by_status(member_tags, TagCurrentStatus.LOST),
                    registered_count=self._count_tags_by_status(member_tags, TagCurrentStatus.REGISTERED),
                )
            )
        return member_summaries

    def _build_dashboard_summary(self, family_members, tag_statuses) -> DashboardSummaryResponse:
        return DashboardSummaryResponse(
            total_members=len(family_members),
            total_tags=len(tag_statuses),
            found_count=self._count_tags_by_status(tag_statuses, TagCurrentStatus.FOUND),
            lost_count=self._count_tags_by_status(tag_statuses, TagCurrentStatus.LOST),
            registered_count=self._count_tags_by_status(tag_statuses, TagCurrentStatus.REGISTERED),
        )

    def _filter_tags_by_owner(self, tag_statuses: list[TagStatusResponse], owner_user_id: int) -> list[TagStatusResponse]:
        return [tag for tag in tag_statuses if tag.owner_user_id == owner_user_id]

    def _build_family_tag_statuses(self, family_id: int, family_members) -> list[TagStatusResponse]:
        tags = self.tag_repository.find_active_by_family_id(family_id)

        member_by_user_id, user_device_map, item_lookup, latest_scan_logs = self._prepare_tag_status_lookup_data(family_id, family_members)

        tag_statuses = []
        for tag in tags:
            tag_status = self._create_tag_status_response(tag, member_by_user_id, user_device_map, item_lookup, latest_scan_logs)
            tag_statuses.append(tag_status)

        return tag_statuses

    def _prepare_tag_status_lookup_data(self, family_id: int, family_members):
        member_by_user_id = {member.user_id: member for member in family_members}
        user_device_map = self._build_family_user_device_map(family_id, family_members)
        item_lookup = self._build_item_lookup_by_owner_and_tag_uid(user_device_map)
        latest_scan_logs = self._get_latest_scan_logs_for_items(item_lookup)

        return member_by_user_id, user_device_map, item_lookup, latest_scan_logs

    def _create_tag_status_response(self, tag, member_by_user_id, user_device_map, item_lookup, latest_scan_logs) -> TagStatusResponse:
        owner_member = member_by_user_id.get(tag.owner_user_id)
        item = item_lookup.get((tag.owner_user_id, tag.tag_uid))
        latest_log = latest_scan_logs.get(item.id) if item else None

        return self._build_tag_status_response(
            tag=tag,
            owner_member=owner_member,
            item=item,
            latest_log=latest_log,
            user_device_by_id=user_device_map
        )

    def _build_family_user_device_map(self, family_id: int, family_members) -> dict[int, object]:
        user_ids = [member.user_id for member in family_members]
        family_user_devices = self._filter_family_user_devices(
            self.user_device_repository.find_all_by_user_ids(user_ids),
            family_id
        )
        return {user_device.id: user_device for user_device in family_user_devices}

    def _filter_family_user_devices(self, user_devices, family_id: int):
        return [
            user_device
            for user_device in user_devices
            if user_device.device and user_device.device.family_id == family_id
        ]

    def _build_item_lookup_by_owner_and_tag_uid(self, user_device_by_id: dict[int, object]) -> dict[tuple[int, str], object]:
        items = self.item_repository.get_active_items_by_user_device_ids(list(user_device_by_id.keys()))

        item_lookup = {}
        for item in items:
            owner_user_device = user_device_by_id.get(item.user_device_id)
            if owner_user_device:
                lookup_key = (owner_user_device.user_id, item.tag_uid)
                if lookup_key not in item_lookup:
                    item_lookup[lookup_key] = item

        return item_lookup

    def _get_latest_scan_logs_for_items(self, item_lookup: dict) -> dict:
        item_ids = [item.id for item in item_lookup.values()]
        return self.scan_log_repository.find_latest_by_item_ids(item_ids)

    def _build_tag_status_response(
        self,
        tag,
        owner_member,
        item,
        latest_log,
        user_device_by_id: dict[int, object]
    ) -> TagStatusResponse:
        last_seen_at = normalize_datetime(latest_log.scanned_at) if latest_log else None
        latest_user_device = user_device_by_id.get(latest_log.user_device_id) if latest_log else None
        status = self._calculate_tag_current_status(item is not None, latest_log.status if latest_log else None)

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

    @staticmethod
    def _calculate_tag_current_status(
        has_linked_item: bool,
        latest_scan_status: str | None
    ) -> TagCurrentStatus:
        if not has_linked_item or latest_scan_status is None:
            return TagCurrentStatus.REGISTERED
        if latest_scan_status == ScanStatus.FOUND.value:
            return TagCurrentStatus.FOUND
        if latest_scan_status == ScanStatus.LOST.value:
            return TagCurrentStatus.LOST
        return TagCurrentStatus.REGISTERED

    @staticmethod
    def _count_tags_by_status(tags: list[TagStatusResponse], status: TagCurrentStatus) -> int:
        return sum(1 for tag in tags if tag.status == status)