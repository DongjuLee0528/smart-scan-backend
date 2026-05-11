"""
Unit tests for inbound-scanner services/scan_service.py

Run: PYTHONPATH=lambdas/inbound-scanner pytest lambdas/inbound-scanner/tests/ -v
"""
import json
import pytest
from unittest.mock import patch, MagicMock


def _make_event(body: dict) -> dict:
    return {"body": json.dumps(body)}


# ── test_missing_device_serial ────────────────────────────────────────────────

def test_missing_device_serial():
    """device_serial이 없으면 400을 반환해야 한다."""
    from services.scan_service import process_scan

    response = process_scan(_make_event({"tags": ["TAG001"]}))

    assert response["statusCode"] == 400
    assert "device_serial" in json.loads(response["body"])["message"]


# ── test_invalid_tags_type ────────────────────────────────────────────────────

@patch("services.scan_service.get_device_by_serial", return_value={"id": 42})
@patch("services.scan_service._insert_scan_logs")
def test_invalid_tags_type(mock_logs, mock_device):
    """tags가 list가 아니면 400을 반환해야 한다."""
    from services.scan_service import process_scan

    response = process_scan(_make_event({"device_serial": "SN-001", "tags": "TAG001"}))

    assert response["statusCode"] == 400
    assert json.loads(response["body"])["message"] == "tags must be an array."


# ── test_device_not_found ─────────────────────────────────────────────────────

@patch("services.scan_service.get_device_by_serial", return_value=None)
def test_device_not_found(mock_device):
    """등록되지 않은 디바이스이면 400을 반환해야 한다."""
    from services.scan_service import process_scan

    response = process_scan(_make_event({"device_serial": "SN-9999", "tags": []}))

    assert response["statusCode"] == 400
    mock_device.assert_called_once_with("SN-9999")


# ── test_no_missing_items ─────────────────────────────────────────────────────

@patch("services.scan_service.lambda_client")
@patch("services.scan_service.check_missing_items_rpc", return_value=[])
@patch("services.scan_service._insert_scan_logs")
@patch("services.scan_service.get_device_by_serial", return_value={"id": 42})
def test_no_missing_items(mock_device, mock_logs, mock_rpc, mock_lambda):
    """누락 물건이 없으면 outbound를 invoke하지 않고 200을 반환해야 한다."""
    from services.scan_service import process_scan

    response = process_scan(_make_event({"device_serial": "SN-001", "tags": ["TAG001"]}))

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["message"] == "All items confirmed."
    mock_lambda.invoke.assert_not_called()


# ── test_missing_items_invokes_outbound ───────────────────────────────────────

@patch("services.scan_service.lambda_client")
@patch(
    "services.scan_service.check_missing_items_rpc",
    return_value=[{
        "member_id": 1, "member_name": "홍길동",
        "member_email": "test@test.com", "missing_item": "지갑"
    }],
)
@patch("services.scan_service._insert_scan_logs")
@patch("services.scan_service.get_device_by_serial", return_value={"id": 42})
def test_missing_items_invokes_outbound(mock_device, mock_logs, mock_rpc, mock_lambda):
    """누락 물건이 있으면 outbound Lambda를 invoke하고 200을 반환해야 한다."""
    from services.scan_service import process_scan

    response = process_scan(_make_event({"device_serial": "SN-001", "tags": []}))

    assert response["statusCode"] == 200
    assert "지갑" in json.loads(response["body"])["message"]
    mock_lambda.invoke.assert_called_once()
    kwargs = mock_lambda.invoke.call_args.kwargs
    assert kwargs["FunctionName"] == "smartscan-outbound"
    assert kwargs["InvocationType"] == "Event"


# ── test_outbound_failure_doesnt_affect_response ──────────────────────────────

@patch("services.scan_service.lambda_client")
@patch(
    "services.scan_service.check_missing_items_rpc",
    return_value=[{
        "member_id": 1, "member_name": "홍길동",
        "member_email": "test@test.com", "missing_item": "지갑"
    }],
)
@patch("services.scan_service._insert_scan_logs")
@patch("services.scan_service.get_device_by_serial", return_value={"id": 42})
def test_outbound_failure_doesnt_affect_response(mock_device, mock_logs, mock_rpc, mock_lambda):
    """outbound invoke 실패해도 200을 반환해야 한다."""
    from services.scan_service import process_scan

    mock_lambda.invoke.side_effect = Exception("Connection timeout")

    response = process_scan(_make_event({"device_serial": "SN-001", "tags": []}))

    assert response["statusCode"] == 200


# ── test_invalid_body_json ────────────────────────────────────────────────────

def test_invalid_body_json():
    """잘못된 JSON body이면 400을 반환해야 한다."""
    from services.scan_service import process_scan

    response = process_scan({"body": "not-json"})

    assert response["statusCode"] == 400
