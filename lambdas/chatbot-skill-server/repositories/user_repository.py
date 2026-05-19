"""
User query repository

Uses only the new schema based on the `users` table.
(magic link integration completed user = user with actual Kakao UID stored in `users.kakao_user_id`)

When querying, `pending_` prefix indicates web signup completed but Kakao integration incomplete, so returns None.
"""
import uuid

from common.db import get_client


# ---------------------------------------------------------------------------
# Internal: users table → family_members → user_devices join query
# ---------------------------------------------------------------------------

def _get_user_from_users_table(kakao_user_id: str):
    """
    Query kakao_user_id from users table →
    Query family_members, user_devices sequentially to
    return {kakao_user_id, member_id, device_id, user_id}.

    Values starting with pending_ indicate incomplete integration, so return None.
    """
    client = get_client()

    user_res = (
        client.table("users")
        .select("id, kakao_user_id")
        .eq("kakao_user_id", kakao_user_id)
        .limit(1)
        .execute()
    )
    if not user_res.data:
        return None

    row = user_res.data[0]
    if row["kakao_user_id"].startswith("pending_"):
        return None

    user_id = row["id"]

    member_res = (
        client.table("family_members")
        .select("id")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not member_res.data:
        return None

    member_id = member_res.data[0]["id"]

    device_res = (
        client.table("user_devices")
        .select("device_id")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    device_id = device_res.data[0]["device_id"] if device_res.data else None

    return {
        "kakao_user_id": kakao_user_id,
        "user_id": user_id,
        "member_id": member_id,
        "device_id": device_id,
    }


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def get_user_by_kakao_id(kakao_user_id: str):
    """
    Query user by kakao_user_id → {kakao_user_id, user_id, device_id, member_id} or None
    """
    return _get_user_from_users_table(kakao_user_id)


def delete_user_device(kakao_user_id: str):
    """
    Disconnect Kakao integration. Reset users.kakao_user_id to `pending_<uuid>` so
    the user can re-integrate using magic link again.
    """
    new_pending = f"pending_{uuid.uuid4().hex}"
    (
        get_client()
        .table("users")
        .update({"kakao_user_id": new_pending})
        .eq("kakao_user_id", kakao_user_id)
        .execute()
    )
