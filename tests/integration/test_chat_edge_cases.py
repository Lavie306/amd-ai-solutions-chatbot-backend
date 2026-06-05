"""
Integration tests cho chat endpoint — edge cases.
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def mock_agent(monkeypatch):
    import app.api.routes.chat as chat_route

    async def mock_handle_chat(**kwargs):
        return {
            "reply": "Xin chào! AMD có thể giúp gì cho bạn?",
            "intent": "general_faq",
            "lead_state": "IDLE",
            "collected_fields": {},
        }
    monkeypatch.setattr(chat_route, "handle_chat", mock_handle_chat)
    return mock_handle_chat


@pytest.mark.asyncio
async def test_chat_empty_message(mock_agent, client: AsyncClient) -> None:
    """Tin nhắn rỗng vẫn trả về reply."""
    import uuid
    sid = str(uuid.uuid4())
    res = await client.post(
        "/api/chat",
        json={"session_id": sid, "message": ""},
    )
    assert res.status_code == 200
    assert "reply" in res.json()


@pytest.mark.asyncio
async def test_chat_very_long_message(mock_agent, client: AsyncClient) -> None:
    """Tin nhắn quá dài (>2000 ký tự) bị từ chối."""
    import uuid
    sid = str(uuid.uuid4())
    res = await client.post(
        "/api/chat",
        json={"session_id": sid, "message": "A" * 2500},
    )
    assert res.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_chat_special_characters(mock_agent, client: AsyncClient) -> None:
    """Tin nhắn với ký tự đặc biệt vẫn hoạt động."""
    import uuid
    sid = str(uuid.uuid4())
    res = await client.post(
        "/api/chat",
        json={"session_id": sid, "message": "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"},
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_chat_multiple_rapid_requests(mock_agent, client: AsyncClient) -> None:
    """Nhiều request nhanh với cùng session không crash."""
    import uuid
    sid = str(uuid.uuid4())

    for i in range(10):
        res = await client.post(
            "/api/chat",
            json={"session_id": sid, "message": f"Message {i}"},
        )
        assert res.status_code == 200
        assert "reply" in res.json()


@pytest.mark.asyncio
async def test_chat_different_sessions_independent(mock_agent, client: AsyncClient) -> None:
    """Hai session khác nhau hoạt động độc lập."""
    import uuid
    sid1, sid2 = str(uuid.uuid4()), str(uuid.uuid4())

    res1 = await client.post(
        "/api/chat",
        json={"session_id": sid1, "message": "Hello session 1"},
    )
    res2 = await client.post(
        "/api/chat",
        json={"session_id": sid2, "message": "Hello session 2"},
    )
    assert res1.status_code == 200
    assert res2.status_code == 200


@pytest.mark.asyncio
async def test_chat_missing_session_id(mock_agent, client: AsyncClient) -> None:
    """Thiếu session_id → 422."""
    res = await client.post(
        "/api/chat",
        json={"message": "Hello"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_chat_missing_message(mock_agent, client: AsyncClient) -> None:
    """Thiếu message → 422."""
    import uuid
    res = await client.post(
        "/api/chat",
        json={"session_id": str(uuid.uuid4())},
    )
    assert res.status_code == 422
