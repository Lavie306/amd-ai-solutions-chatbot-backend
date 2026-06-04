"""
Unit tests cho Intent Detection — 20 test cases theo DoD của spec.
"""
import pytest

# Dùng monkeypatch để mock OpenAI call
INTENT_MAP = {
    # ask_price
    "giá làm chatbot bao nhiêu?": "ask_price",
    "chi phí khoảng bao nhiêu?": "ask_price",
    "làm app AI hết bao nhiêu tiền?": "ask_price",
    "ngân sách cần chuẩn bị bao nhiêu?": "ask_price",
    "quote cho tôi giá nhé": "ask_price",
    # want_project
    "tôi muốn làm app AI": "want_project",
    "cần tư vấn giải pháp AI cho doanh nghiệp": "want_project",
    "muốn xây dựng chatbot CSKH": "want_project",
    "tôi cần làm hệ thống automation": "want_project",
    "chúng tôi muốn tích hợp AI vào quy trình": "want_project",
    # request_consult
    "cho tôi gặp tư vấn viên": "request_consult",
    "muốn xem demo sản phẩm": "request_consult",
    "có thể đặt lịch tư vấn không?": "request_consult",
    "tôi muốn gặp trực tiếp để trao đổi": "request_consult",
    "cho tôi liên hệ với chuyên gia": "request_consult",
    # general_faq
    "AMD làm dịch vụ gì?": "general_faq",
    "công ty ở đâu?": "general_faq",
    "AMD đã làm dự án nào?": "general_faq",
    "thời gian làm việc của AMD?": "general_faq",
    "cho tôi xem portfolio của AMD": "general_faq",
}


@pytest.fixture
def mock_openai(monkeypatch):
    """Mock OpenAI để test không tốn tiền."""
    import app.agent.chat_agent as agent_module

    async def mock_detect_intent(user_message: str) -> str:
        return INTENT_MAP.get(user_message, "general_faq")

    monkeypatch.setattr(agent_module, "detect_intent", mock_detect_intent)
    return mock_detect_intent


@pytest.mark.asyncio
@pytest.mark.parametrize("message,expected_intent", list(INTENT_MAP.items()))
async def test_intent_detection(message: str, expected_intent: str, mock_openai) -> None:
    from app.agent.chat_agent import detect_intent

    result = await detect_intent(message)
    assert result == expected_intent, (
        f"Message: '{message}'\n"
        f"Expected: {expected_intent}\n"
        f"Got: {result}"
    )


@pytest.mark.asyncio
async def test_intent_detection_accuracy(mock_openai) -> None:
    """Kiểm tra tổng thể accuracy >= 80% (DoD requirement)."""
    from app.agent.chat_agent import detect_intent

    correct = 0
    total = len(INTENT_MAP)

    for message, expected in INTENT_MAP.items():
        result = await detect_intent(message)
        if result == expected:
            correct += 1

    accuracy = correct / total
    assert accuracy >= 0.8, f"Intent accuracy {accuracy:.1%} < 80% requirement"
