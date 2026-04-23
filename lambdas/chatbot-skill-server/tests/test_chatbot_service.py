"""
Unit tests for chatbot_service.py

PYTHONPATH 설정 예시:
    PYTHONPATH=lambdas/chatbot-skill-server pytest lambdas/chatbot-skill-server/tests/ -v
"""
import json
import unittest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# 헬퍼 — 공통 요청 빌더
# ---------------------------------------------------------------------------

def _body(utterance: str, kakao_user_id: str = "kakao-uid-001") -> dict:
    """카카오 챗봇 요청 형식의 body 딕셔너리 생성."""
    return {
        "userRequest": {
            "user": {"id": kakao_user_id},
            "utterance": utterance,
        }
    }


def _kakao_text(resp: dict) -> str:
    """simpleText 응답에서 텍스트 추출.
    응답 구조: {'statusCode': 200, 'body': '{"version":"2.0","template":{"outputs":[{"simpleText":{"text":"..."}}]}}'}
    """
    body = json.loads(resp["body"])
    return body["template"]["outputs"][0]["simpleText"]["text"]


def _kakao_card(resp: dict) -> dict:
    """basicCard 응답에서 카드 dict 추출."""
    body = json.loads(resp["body"])
    return body["template"]["outputs"][0]["basicCard"]


# ---------------------------------------------------------------------------
# 테스트 클래스
# ---------------------------------------------------------------------------

class TestHandleChatbot(unittest.TestCase):

    # 1. kakao_user_id 없음 → 에러 메시지 반환
    def test_no_kakao_user_id(self):
        from services.chatbot_service import handle_chatbot

        body = {"userRequest": {"user": {}, "utterance": "목록"}}
        resp = handle_chatbot(body)

        text = _kakao_text(resp)
        self.assertIn("카카오 사용자 ID", text)

    # 2. get_user_by_kakao_id → None → magic link 포함 basicCard 반환
    @patch("services.chatbot_service.create_kakao_link_token", return_value="mock.jwt.token")
    @patch("services.chatbot_service.get_user_by_kakao_id", return_value=None)
    def test_no_device_linked_returns_magic_link(self, _mock_user, _mock_token):
        from services.chatbot_service import handle_chatbot

        resp = handle_chatbot(_body("목록"))

        card = _kakao_card(resp)
        # 안내 메시지 포함 확인
        self.assertIn("연동", card["description"])
        # 링크 버튼 포함 확인
        buttons = card["buttons"]
        self.assertEqual(len(buttons), 1)
        self.assertEqual(buttons[0]["action"], "webLink")
        self.assertIn("link-kakao", buttons[0]["webLinkUrl"])
        self.assertIn("mock.jwt.token", buttons[0]["webLinkUrl"])

    # 3. magic link 토큰이 kakao_user_id 포함 확인
    @patch("services.chatbot_service.get_user_by_kakao_id", return_value=None)
    def test_magic_link_token_called_with_kakao_user_id(self, _mock_user):
        from services.chatbot_service import handle_chatbot

        with patch("services.chatbot_service.create_kakao_link_token", return_value="tok") as mock_token:
            handle_chatbot(_body("목록", kakao_user_id="my-kakao-id"))
            mock_token.assert_called_once_with("my-kakao-id")

    # 4. '목록' 발화 → _handle_list 호출 (items 2개)
    @patch("services.chatbot_service.get_active_items",
           return_value=[{"name": "지갑"}, {"name": "열쇠"}])
    @patch("services.chatbot_service.get_user_by_kakao_id",
           return_value={"member_id": 10})
    def test_list_utterance(self, _mock_user, _mock_items):
        from services.chatbot_service import handle_chatbot

        resp = handle_chatbot(_body("목록 보여줘"))

        text = _kakao_text(resp)
        self.assertIn("지갑", text)
        self.assertIn("열쇠", text)
        _mock_items.assert_called_once_with("kakao-uid-001")

    # 5. '목록' 발화 — items 없을 때 → 등록 없음 메시지
    @patch("services.chatbot_service.get_active_items", return_value=[])
    @patch("services.chatbot_service.get_user_by_kakao_id",
           return_value={"member_id": 10})
    def test_list_utterance_empty(self, _mock_user, _mock_items):
        from services.chatbot_service import handle_chatbot

        resp = handle_chatbot(_body("물건 목록"))

        text = _kakao_text(resp)
        self.assertIn("등록된 소지품이 없습니다", text)

    # 6. '지갑 추가' → add_item 호출
    @patch("services.chatbot_service.add_item")
    @patch("services.chatbot_service.get_active_items", return_value=[])
    @patch("services.chatbot_service.get_user_by_kakao_id",
           return_value={"member_id": 10})
    def test_add_utterance(self, _mock_user, _mock_items, mock_add):
        from services.chatbot_service import handle_chatbot

        resp = handle_chatbot(_body("지갑 추가"))

        text = _kakao_text(resp)
        self.assertIn("지갑", text)
        self.assertIn("추가", text)
        mock_add.assert_called_once_with("지갑", "kakao-uid-001")

    # 7. 이미 존재하는 물건 추가 → 중복 메시지
    @patch("services.chatbot_service.add_item")
    @patch("services.chatbot_service.get_active_items",
           return_value=[{"name": "지갑"}])
    @patch("services.chatbot_service.get_user_by_kakao_id",
           return_value={"member_id": 10})
    def test_add_duplicate(self, _mock_user, _mock_items, mock_add):
        from services.chatbot_service import handle_chatbot

        resp = handle_chatbot(_body("지갑 추가"))

        text = _kakao_text(resp)
        self.assertIn("이미 등록", text)
        mock_add.assert_not_called()

    # 8. '지갑 삭제' → deactivate_item 호출 (count=1)
    @patch("services.chatbot_service.deactivate_item", return_value=1)
    @patch("services.chatbot_service.get_user_by_kakao_id",
           return_value={"member_id": 10})
    def test_delete_utterance(self, _mock_user, mock_deactivate):
        from services.chatbot_service import handle_chatbot

        resp = handle_chatbot(_body("지갑 삭제"))

        text = _kakao_text(resp)
        self.assertIn("지갑", text)
        self.assertIn("삭제", text)
        mock_deactivate.assert_called_once_with("지갑", "kakao-uid-001")

    # 9. deactivate_item 0 반환 → 찾을 수 없음 메시지
    @patch("services.chatbot_service.deactivate_item", return_value=0)
    @patch("services.chatbot_service.get_user_by_kakao_id",
           return_value={"member_id": 10})
    def test_delete_not_found(self, _mock_user, _mock_deactivate):
        from services.chatbot_service import handle_chatbot

        resp = handle_chatbot(_body("안경 삭제"))

        text = _kakao_text(resp)
        self.assertIn("찾을 수 없습니다", text)

    # 10. '기기 해제' → delete_all_items + delete_user_device 모두 호출
    @patch("services.chatbot_service.delete_user_device")
    @patch("services.chatbot_service.delete_all_items")
    @patch("services.chatbot_service.get_user_by_kakao_id",
           return_value={"member_id": 10})
    def test_disconnect_utterance(self, _mock_user, mock_delete_items,
                                  mock_delete_device):
        from services.chatbot_service import handle_chatbot

        resp = handle_chatbot(_body("기기 해제"))

        text = _kakao_text(resp)
        self.assertIn("해제", text)
        mock_delete_items.assert_called_once_with("kakao-uid-001")
        mock_delete_device.assert_called_once_with("kakao-uid-001")

    # 11. 알 수 없는 발화 → 명령어 안내 메시지
    @patch("services.chatbot_service.get_user_by_kakao_id",
           return_value={"member_id": 10})
    def test_unknown_utterance(self, _mock_user):
        from services.chatbot_service import handle_chatbot

        resp = handle_chatbot(_body("안녕하세요 오늘 날씨 어때요"))

        text = _kakao_text(resp)
        self.assertIn("명령어를 이해하지 못했습니다", text)


if __name__ == "__main__":
    unittest.main()
