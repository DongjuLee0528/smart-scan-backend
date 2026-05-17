"""
Item repository for KakaoTalk chatbot (HTTP client)

Refactored (2026-04-18): To eliminate 500 errors due to schema drift (`items.is_required`, `items.member_id` not existing),
changed from direct Supabase access → SmartScan FastAPI `/api/chatbot/*` HTTP calls.

Authentication: Pass shared secret via `X-Chatbot-Key` header. (Separate secret isolated from JWT)

Environment variables:
- SMARTSCAN_API_BASE: FastAPI base URL (default: https://smartscan-hub.com)
- CHATBOT_SHARED_KEY: Shared secret (same value as server)
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


_API_BASE = os.environ.get("SMARTSCAN_API_BASE", "https://smartscan-hub.com").rstrip("/")
_SHARED_KEY = os.environ.get("CHATBOT_SHARED_KEY", "")
_DEFAULT_TIMEOUT_SEC = 8.0


class ChatbotApiError(RuntimeError):
    """Explicitly signal backend call failure."""


def _request(method: str, path: str, *, params: dict | None = None, body: dict | None = None) -> Any:
    url = f"{_API_BASE}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    data = None
    headers = {
        "X-Chatbot-Key": _SHARED_KEY,
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url=url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=_DEFAULT_TIMEOUT_SEC) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
        print(f"[ChatbotApi] HTTPError {exc.code} {method} {url}: {detail}")
        raise ChatbotApiError(f"backend {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        print(f"[ChatbotApi] URLError {method} {url}: {exc}")
        raise ChatbotApiError(f"backend unreachable: {exc}") from exc

    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise ChatbotApiError(f"invalid JSON from backend: {raw[:200]}") from exc

    if not isinstance(payload, dict) or not payload.get("success", False):
        raise ChatbotApiError(f"backend returned failure: {payload}")

    return payload.get("data")


def get_active_items(kakao_user_id: str) -> list:
    """
    Query active item list (including pending).

    Returns:
        list[dict]: [{id, name, is_pending, label_id, ...}]
    """
    data = _request("GET", "/api/chatbot/items", params={"kakao_user_id": kakao_user_id})
    if not data:
        return []
    return data.get("items", []) or []


def add_item(name: str, kakao_user_id: str) -> dict | None:
    """Add pending item by name only."""
    return _request(
        "POST",
        "/api/chatbot/items",
        body={"kakao_user_id": kakao_user_id, "name": name},
    )


def deactivate_item(name: str, kakao_user_id: str) -> int:
    """Find active item by name and soft-delete. Return deleted count (0 or 1)."""
    try:
        data = _request(
            "POST",
            "/api/chatbot/items/delete-by-name",
            body={"kakao_user_id": kakao_user_id, "name": name},
        )
    except ChatbotApiError:
        return 0
    if not data:
        return 0
    return int(data.get("deleted_count", 0))


def delete_all_items(kakao_user_id: str) -> int:
    """Batch soft-delete all active items for the user."""
    data = _request(
        "POST",
        "/api/chatbot/device/unlink",
        body={"kakao_user_id": kakao_user_id},
    )
    if not data:
        return 0
    return int(data.get("deleted_count", 0))
