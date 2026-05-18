"""
Unit tests for outbound-notifier services/notify_service.py

PYTHONPATH setting assumption: lambdas/outbound-notifier/
Execute: pytest lambdas/outbound-notifier/tests/
"""
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helper: Create basic member dict
# ---------------------------------------------------------------------------

def _make_member(
    member_id=1,
    member_name="홍길동",
    member_email="hong@example.com",
    missing_items=None,
):
    return {
        "member_id": member_id,
        "member_name": member_name,
        "member_email": member_email,
        "missing_items": missing_items if missing_items is not None else ["item_a"],
    }


# ---------------------------------------------------------------------------
# test_empty_members_returns_skip
# ---------------------------------------------------------------------------

def test_empty_members_returns_skip():
    """missing_by_member가 빈 리스트이면 skip 상태를 반환해야 한다."""
    from services.notify_service import send_missing_alert

    result = send_missing_alert({"missing_by_member": []})

    assert result["status"] == "skip"


# ---------------------------------------------------------------------------
# test_no_email_skipped
# ---------------------------------------------------------------------------

@patch("services.notify_service.get_client")
@patch("services.notify_service.send_email")
def test_no_email_skipped(mock_send_email, mock_get_client):
    """member_email이 없으면 해당 멤버를 skipped 처리해야 한다."""
    from services.notify_service import send_missing_alert

    member = _make_member(member_email=None)
    result = send_missing_alert({"missing_by_member": [member]})

    assert result["status"] == "ok"
    assert result["details"][0]["status"] == "skipped"
    mock_send_email.assert_not_called()


# ---------------------------------------------------------------------------
# test_no_items_skipped
# ---------------------------------------------------------------------------

@patch("services.notify_service.get_client")
@patch("services.notify_service.send_email")
def test_no_items_skipped(mock_send_email, mock_get_client):
    """missing_items가 빈 리스트이면 해당 멤버를 skipped 처리해야 한다."""
    from services.notify_service import send_missing_alert

    member = _make_member(missing_items=[])
    result = send_missing_alert({"missing_by_member": [member]})

    assert result["status"] == "ok"
    assert result["details"][0]["status"] == "skipped"
    mock_send_email.assert_not_called()


# ---------------------------------------------------------------------------
# test_email_sent_success
# ---------------------------------------------------------------------------

@patch("services.notify_service.get_client")
@patch("services.notify_service.send_email", return_value=True)
def test_email_sent_success(mock_send_email, mock_get_client):
    """send_email이 True를 반환하면 status가 'sent'여야 한다."""
    from services.notify_service import send_missing_alert

    mock_supabase = MagicMock()
    mock_get_client.return_value = mock_supabase

    member = _make_member()
    result = send_missing_alert({"missing_by_member": [member]})

    assert result["status"] == "ok"
    assert result["sent"] == 1
    assert result["details"][0]["status"] == "sent"
    mock_send_email.assert_called_once()


# ---------------------------------------------------------------------------
# test_email_failed
# ---------------------------------------------------------------------------

@patch("services.notify_service.get_client")
@patch("services.notify_service.send_email", return_value=False)
def test_email_failed(mock_send_email, mock_get_client):
    """send_email이 False를 반환하면 status가 'email_failed'여야 한다."""
    from services.notify_service import send_missing_alert

    mock_supabase = MagicMock()
    mock_get_client.return_value = mock_supabase

    member = _make_member()
    result = send_missing_alert({"missing_by_member": [member]})

    assert result["status"] == "ok"
    assert result["sent"] == 0
    assert result["details"][0]["status"] == "email_failed"


# ---------------------------------------------------------------------------
# test_db_failure_doesnt_affect_result
# ---------------------------------------------------------------------------

@patch("services.notify_service.get_client")
@patch("services.notify_service.send_email", return_value=True)
def test_db_failure_doesnt_affect_result(mock_send_email, mock_get_client):
    """DB insert에서 예외가 발생해도 결과는 'sent'여야 한다."""
    from services.notify_service import send_missing_alert

    mock_supabase = MagicMock()
    mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception(
        "DB connection error"
    )
    mock_get_client.return_value = mock_supabase

    member = _make_member()
    result = send_missing_alert({"missing_by_member": [member]})

    assert result["status"] == "ok"
    assert result["details"][0]["status"] == "sent"


# ---------------------------------------------------------------------------
# test_xss_escape
# ---------------------------------------------------------------------------

@patch("services.notify_service.get_client")
@patch("services.notify_service.send_email", return_value=True)
def test_xss_escape(mock_send_email, mock_get_client):
    """member_name에 <script> 태그가 포함되면 HTML escape 처리되어야 한다."""
    from services.notify_service import send_missing_alert

    mock_supabase = MagicMock()
    mock_get_client.return_value = mock_supabase

    member = _make_member(member_name="<script>alert('xss')</script>")
    send_missing_alert({"missing_by_member": [member]})

    # send_email에 전달된 html 본문 검사
    call_args = mock_send_email.call_args
    html_body = call_args[0][2]  # positional: (recipients, subject, html)

    assert "<script>" not in html_body
    assert "&lt;script&gt;" in html_body


# ---------------------------------------------------------------------------
# test_multiple_members
# ---------------------------------------------------------------------------

@patch("services.notify_service.get_client")
@patch("services.notify_service.send_email")
def test_multiple_members(mock_send_email, mock_get_client):
    """2명 처리 시 send_email 결과에 따라 sent_count가 정확히 계산되어야 한다."""
    from services.notify_service import send_missing_alert

    mock_supabase = MagicMock()
    mock_get_client.return_value = mock_supabase

    # 첫 번째 멤버: 이메일 성공, 두 번째 멤버: 이메일 실패
    mock_send_email.side_effect = [True, False]

    members = [
        _make_member(member_id=1, member_email="user1@example.com"),
        _make_member(member_id=2, member_email="user2@example.com"),
    ]
    result = send_missing_alert({"missing_by_member": members})

    assert result["status"] == "ok"
    assert result["total"] == 2
    assert result["sent"] == 1
    assert result["details"][0]["status"] == "sent"
    assert result["details"][1]["status"] == "email_failed"
    assert mock_send_email.call_count == 2
