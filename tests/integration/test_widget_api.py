"""
Integration tests for the Public Widget/Settings config API.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest.mark.asyncio
async def test_get_public_config_success(client: AsyncClient) -> None:
    # Get config without any Auth header (public access)
    response = await client.get("/api/settings/public/config")
    assert response.status_code == 200
    data = response.json()
    
    assert "bot_name" in data
    assert "welcome_message" in data
    assert "handoff_message" in data
    assert "zalo_number" in data
    assert "language" in data
    
    # Verify default values from settings seeding
    assert data["bot_name"] == "AMD Assistant"
    assert "AMD AI Solutions" in data["welcome_message"]
