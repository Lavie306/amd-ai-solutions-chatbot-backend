"""
Integration test cho chat endpoint.
"""
import pytest
from httpx import AsyncClient

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_chat_creates_session(client: AsyncClient, monkeypatch) -> None:
    """Chat với session mới phải trả về reply."""
    from app.agent import chat_agent

    async def mock_handle_chat(**kwargs):
        return {
            "reply": "Xin chào! AMD có thể giúp gì cho bạn?",
            "intent": "general_faq",
            "lead_state": "IDLE",
            "collected_fields": {},
        }

    monkeypatch.setattr(chat_agent, "handle_chat", mock_handle_chat)

    import uuid
    session_id = str(uuid.uuid4())
    response = await client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "AMD làm dịch vụ gì?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert data["session_id"] == session_id
