"""
카카오톡 챗봇용 아이템 리포지토리 (HTTP 클라이언트)

A-full (2026-04-18): 스키마 드리프트로 인한 500 오류(`items.is_required`, `items.member_id` 존재 X)를
제거하기 위해 Supabase 직접 접근 → SmartScan FastAPI `/api/chatbot/*` HTTP 호출로 전환.

인증: 공유 비밀키를 `X-Chatbot-Key` 헤더로 전달. (JWT와 격리된 별도 시크릿)

환경변수:
- SMARTSCAN_API_BASE: FastAPI 베이스 URL (기본: https://smartscan-hub.com)
- CHATBOT_SHARED_KEY: 공유 비밀키 (서버와 동일 값)
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
    """백엔드 호출 실패를 명시적으로 시그널링."""


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
    활성 아이템 목록 조회 (pending 포함).

    Returns:
        list[dict]: [{id, name, is_pending, label_id, ...}]
    """
    data = _request("GET", "/api/chatbot/items", params={"kakao_user_id": kakao_user_id})
    if not data:
        return []
    return data.get("items", []) or []


def add_item(name: str, kakao_user_id: str) -> dict | None:
    """이름만으로 pending 아이템 추가."""
    return _request(
        "POST",
        "/api/chatbot/items",
        body={"kakao_user_id": kakao_user_id, "name": name},
    )


def deactivate_item(name: str, kakao_user_id: str) -> int:
    """이름으로 활성 아이템을 찾아 soft-delete. 삭제된 개수 반환 (0 or 1)."""
    data = _request(
        "POST",
        "/api/chatbot/items/delete-by-name",
        body={"kakao_user_id": kakao_user_id, "name": name},
    )
    if not data:
        return 0
    return int(data.get("deleted_count", 0))


def delete_all_items(kakao_user_id: str) -> int:
    """해당 사용자의 모든 활성 아이템 일괄 soft-delete."""
    data = _request(
        "POST",
        "/api/chatbot/device/unlink",
        body={"kakao_user_id": kakao_user_id},
    )
    if not data:
        return 0
    return int(data.get("deleted_count", 0))
