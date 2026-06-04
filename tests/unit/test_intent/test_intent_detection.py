"""
Unit tests cho Intent Detection — 20 test cases theo DoD của spec.
Bao gồm: keyword fallback (unit) + OpenAI primary + fallback integration.
"""
import pytest
from unittest.mock import AsyncMock, patch

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


# ── Keyword Fallback Tests ──────────────────────────────────


@pytest.mark.parametrize("message,expected_intent", [
    (m, e) for m, e in INTENT_MAP.items() if e != "general_faq"
])
def test_keyword_detection_lead_intents(message: str, expected_intent: str) -> None:
    """Keyword fallback detect đúng các lead intent."""
    from app.agent.chat_agent import detect_intent_keyword

    result = detect_intent_keyword(message)
    assert result == expected_intent, (
        f"Message: '{message}'\nExpected: {expected_intent}\nGot: {result}"
    )


@pytest.mark.parametrize("message", [
    m for m, e in INTENT_MAP.items() if e == "general_faq"
])
def test_keyword_detection_general_faq(message: str) -> None:
    """general_faq không khớp keyword nào → trả về None."""
    from app.agent.chat_agent import detect_intent_keyword

    result = detect_intent_keyword(message)
    assert result is None, (
        f"Message: '{message}'\nExpected: None (general_faq)\nGot: {result}"
    )


def test_keyword_accuracy() -> None:
    """>=80% accuracy trên 20 test cases (keyword fallback path)."""
    from app.agent.chat_agent import detect_intent_keyword

    correct = 0
    for message, expected in INTENT_MAP.items():
        result = detect_intent_keyword(message)
        if expected == "general_faq":
            if result is None:
                correct += 1
        elif result == expected:
            correct += 1

    accuracy = correct / len(INTENT_MAP)
    assert accuracy >= 0.8, f"Keyword intent accuracy {accuracy:.1%} < 80% requirement"


# ── OpenAI Path Tests (with client mock) ────────────────────


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client để test detect_intent không tốn phí."""
    with patch("app.agent.chat_agent.client") as mock:
        mock.chat.completions.create = AsyncMock()
        yield mock


@pytest.mark.asyncio
@pytest.mark.parametrize("message,expected_intent", list(INTENT_MAP.items()))
async def test_detect_intent_openai_success(
    message: str, expected_intent: str, mock_openai_client
) -> None:
    """OpenAI thành công → trả về intent từ API."""
    from app.agent.chat_agent import detect_intent

    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock()]
    mock_response.choices[0].message.content = expected_intent
    mock_openai_client.chat.completions.create.return_value = mock_response

    result = await detect_intent(message)
    assert result == expected_intent, (
        f"Message: '{message}'\nExpected: {expected_intent}\nGot: {result}"
    )


@pytest.mark.asyncio
async def test_detect_intent_openai_fallback(mock_openai_client) -> None:
    """OpenAI fail → fallback sang keyword detection."""
    from app.agent.chat_agent import detect_intent

    mock_openai_client.chat.completions.create.side_effect = Exception("OpenAI unavailable")

    result = await detect_intent("giá làm chatbot bao nhiêu?")
    assert result == "ask_price"

    result = await detect_intent("công ty ở đâu?")
    assert result == "general_faq"


@pytest.mark.asyncio
async def test_detect_intent_openai_invalid_response(mock_openai_client) -> None:
    """OpenAI trả về intent không hợp lệ → fallback keyword."""
    from app.agent.chat_agent import detect_intent

    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock()]
    mock_response.choices[0].message.content = "invalid_intent_xyz"
    mock_openai_client.chat.completions.create.return_value = mock_response

    result = await detect_intent("báo giá chatbot")
    assert result == "ask_price"
