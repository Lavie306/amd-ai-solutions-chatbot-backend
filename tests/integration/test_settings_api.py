"""
Integration tests cho Settings API (key-value CRUD).
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import get_settings

settings = get_settings()


@pytest.fixture
def admin_headers():
    from app.core.security import create_access_token
    token = create_access_token(settings.admin_email)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_get_all_settings_empty(client: AsyncClient, admin_headers) -> None:
    res = await client.get("/api/settings", headers=admin_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


@pytest.mark.asyncio
async def test_upsert_setting(client: AsyncClient, admin_headers) -> None:
    res = await client.put(
        "/api/settings/bot_name",
        json={"value": "AMD Assistant"},
        headers=admin_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["key"] == "bot_name"
    assert data["value"] == "AMD Assistant"


@pytest.mark.asyncio
async def test_get_setting(client: AsyncClient, admin_headers) -> None:
    res = await client.get("/api/settings/bot_name", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["key"] == "bot_name"
    assert data["value"] == "AMD Assistant"


@pytest.mark.asyncio
async def test_get_setting_not_found(client: AsyncClient, admin_headers) -> None:
    res = await client.get("/api/settings/nonexistent_key", headers=admin_headers)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_upsert_setting_json_value(client: AsyncClient, admin_headers) -> None:
    res = await client.put(
        "/api/settings/lead_fields",
        json={"value": [{"key": "name", "label": "Tên", "enabled": True}]},
        headers=admin_headers,
    )
    assert res.status_code == 200
    assert res.json()["value"] == [{"key": "name", "label": "Tên", "enabled": True}]


@pytest.mark.asyncio
async def test_delete_setting(client: AsyncClient, admin_headers) -> None:
    # Upsert first
    await client.put("/api/settings/temp_key", json={"value": "temp_value"}, headers=admin_headers)

    res = await client.delete("/api/settings/temp_key", headers=admin_headers)
    assert res.status_code == 204

    # Verify deleted
    get_res = await client.get("/api/settings/temp_key", headers=admin_headers)
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_delete_setting_not_found(client: AsyncClient, admin_headers) -> None:
    res = await client.delete("/api/settings/nonexistent_key", headers=admin_headers)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_settings_unauthorized(client: AsyncClient) -> None:
    res = await client.get("/api/settings")
    assert res.status_code in (401, 403)
