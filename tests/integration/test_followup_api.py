"""
Integration tests cho Follow-up API (rules CRUD + jobs list/cancel).
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


# ── Rules ──────────────────────────────────


@pytest.mark.asyncio
async def test_list_rules_empty(client: AsyncClient, admin_headers) -> None:
    res = await client.get("/api/followup/rules", headers=admin_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


@pytest.mark.asyncio
async def test_create_rule(client: AsyncClient, admin_headers) -> None:
    res = await client.post(
        "/api/followup/rules",
        json={
            "trigger_status": "QUOTED",
            "delay_days": 3,
            "action_type": "email_customer",
            "template": "Chào {{name}}, ...",
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["trigger_status"] == "QUOTED"
    assert data["delay_days"] == 3
    assert data["action_type"] == "email_customer"
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_list_rules_after_create(client: AsyncClient, admin_headers) -> None:
    res = await client.get("/api/followup/rules", headers=admin_headers)
    assert res.status_code == 200
    rules = res.json()
    assert len(rules) >= 1


@pytest.mark.asyncio
async def test_update_rule(client: AsyncClient, admin_headers) -> None:
    list_res = await client.get("/api/followup/rules", headers=admin_headers)
    rule_id = list_res.json()[-1]["id"]

    res = await client.patch(
        f"/api/followup/rules/{rule_id}",
        json={"delay_days": 5, "is_active": False},
        headers=admin_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["delay_days"] == 5
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_update_rule_not_found(client: AsyncClient, admin_headers) -> None:
    res = await client.patch(
        "/api/followup/rules/999999",
        json={"delay_days": 5},
        headers=admin_headers,
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_delete_rule(client: AsyncClient, admin_headers) -> None:
    list_res = await client.get("/api/followup/rules", headers=admin_headers)
    rule_id = list_res.json()[-1]["id"]

    res = await client.delete(f"/api/followup/rules/{rule_id}", headers=admin_headers)
    assert res.status_code == 204


@pytest.mark.asyncio
async def test_delete_rule_not_found(client: AsyncClient, admin_headers) -> None:
    res = await client.delete("/api/followup/rules/999999", headers=admin_headers)
    assert res.status_code == 404


# ── Jobs ──────────────────────────────────


@pytest.mark.asyncio
async def test_list_jobs_empty(client: AsyncClient, admin_headers) -> None:
    res = await client.get("/api/followup/jobs", headers=admin_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


@pytest.mark.asyncio
async def test_cancel_job_not_found(client: AsyncClient, admin_headers) -> None:
    res = await client.post("/api/followup/jobs/999999/cancel", headers=admin_headers)
    assert res.status_code == 404
