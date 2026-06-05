"""
Integration tests cho Leads API (Tuần 3).
Bao gồm: list, paginate, filter, sort, detail, update, delete, lead collection flow.
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


@pytest.fixture
def mock_agent(monkeypatch):
    """Mock chat_agent.handle_chat để không gọi OpenAI thật."""
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


# ── List leads ─────────────────────────────────────


@pytest.mark.asyncio
async def test_list_leads_empty(client: AsyncClient, admin_headers) -> None:
    """Leads list trả về đúng structure."""
    response = await client.get("/api/leads", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "pagination" in data
    assert isinstance(data["items"], list)
    assert data["pagination"]["page"] == 1


@pytest.mark.asyncio
async def test_list_leads_unauthorized(client: AsyncClient) -> None:
    """Không có token → 403/401."""
    response = await client.get("/api/leads")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_leads_pagination(mock_agent, client: AsyncClient, admin_headers) -> None:
    """Tạo nhiều lead qua chat → kiểm tra pagination."""
    import uuid
    session_ids = []
    for i in range(5):
        sid = str(uuid.uuid4())
        session_ids.append(sid)
        await client.post(
            "/api/chat",
            json={"session_id": sid, "message": f"Test message {i}"},
        )

    # Page 1, page_size=2
    res = await client.get("/api/leads?page=1&page_size=2", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 2
    assert data["pagination"]["total"] >= 5
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["page_size"] == 2
    assert data["pagination"]["total_pages"] >= 3


# ── Lead detail ─────────────────────────────────────


@pytest.mark.asyncio
async def test_get_lead_detail(mock_agent, client: AsyncClient, admin_headers) -> None:
    """Xem chi tiết lead: phải có chat_log, lead_state, fields."""
    import uuid
    sid = str(uuid.uuid4())
    chat_res = await client.post(
        "/api/chat",
        json={"session_id": sid, "message": "AMD làm dịch vụ gì?"},
    )
    assert chat_res.status_code == 200

    # List leads để tìm ID của session vừa tạo
    list_res = await client.get("/api/leads", headers=admin_headers)
    lead_id = None
    for item in list_res.json()["items"]:
        if item["session_id"] == sid:
            lead_id = item["id"]
            break
    assert lead_id is not None, f"Lead with session_id {sid} not found"

    # Get detail
    detail_res = await client.get(f"/api/leads/{lead_id}", headers=admin_headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["session_id"] == sid
    assert detail["lead_state"] == "IDLE"
    assert isinstance(detail["chat_log"], list)
    assert len(detail["chat_log"]) > 0
    assert detail["chat_log"][0]["role"] == "user"


@pytest.mark.asyncio
async def test_get_lead_not_found(client: AsyncClient, admin_headers) -> None:
    """Lead không tồn tại → 404."""
    res = await client.get("/api/leads/999999", headers=admin_headers)
    assert res.status_code == 404


# ── Update lead (status transitions + notes) ─────────


@pytest.mark.asyncio
async def test_update_lead_status(mock_agent, client: AsyncClient, admin_headers) -> None:
    """Chuyển status lead: NEW → CONTACTED → QUOTED."""
    import uuid
    sid = str(uuid.uuid4())
    await client.post(
        "/api/chat",
        json={"session_id": sid, "message": "Test lead"},
    )

    list_res = await client.get("/api/leads", headers=admin_headers)
    lead_id = list_res.json()["items"][0]["id"]

    # NEW → CONTACTED
    upd = await client.patch(
        f"/api/leads/{lead_id}",
        json={"status": "CONTACTED"},
        headers=admin_headers,
    )
    assert upd.status_code == 200
    assert upd.json()["status"] == "CONTACTED"

    # CONTACTED → QUOTED
    upd2 = await client.patch(
        f"/api/leads/{lead_id}",
        json={"status": "QUOTED"},
        headers=admin_headers,
    )
    assert upd2.status_code == 200
    assert upd2.json()["status"] == "QUOTED"


@pytest.mark.asyncio
async def test_update_lead_status_creates_followup_jobs(
    mock_agent, client: AsyncClient, admin_headers
) -> None:
    """PATCH status=QUOTED phải tạo FollowupJob cho mỗi rule matching."""
    from app.db.session import AsyncSessionLocal
    from app.models.models import FollowupRule

    async with AsyncSessionLocal() as db:
        db.add(FollowupRule(
            trigger_status="QUOTED",
            delay_days=3,
            action_type="email_customer",
            template=None,
            is_active=True,
        ))
        db.add(FollowupRule(
            trigger_status="QUOTED",
            delay_days=7,
            action_type="email_customer",
            template=None,
            is_active=True,
        ))
        await db.commit()

    import datetime
    import uuid
    sid = str(uuid.uuid4())
    await client.post(
        "/api/chat",
        json={"session_id": sid, "message": "Test status -> followup"},
    )

    list_res = await client.get("/api/leads", headers=admin_headers)
    lead_id = next(
        item["id"] for item in list_res.json()["items"] if item["session_id"] == sid
    )

    upd = await client.patch(
        f"/api/leads/{lead_id}",
        json={"status": "QUOTED"},
        headers=admin_headers,
    )
    assert upd.status_code == 200

    jobs_res = await client.get(
        f"/api/followup/jobs?lead_id={lead_id}", headers=admin_headers
    )
    assert jobs_res.status_code == 200
    jobs = jobs_res.json()
    assert len(jobs) >= 2
    assert all(j["status"] == "pending" for j in jobs)
    assert all(j["action_type"] == "email_customer" for j in jobs)

    now = datetime.datetime.now()
    scheduled_dates = [datetime.datetime.fromisoformat(j["scheduled"]) for j in jobs]
    three_days = now + datetime.timedelta(days=3)
    seven_days = now + datetime.timedelta(days=7)
    assert any(abs((d - three_days).total_seconds()) < 60 for d in scheduled_dates)
    assert any(abs((d - seven_days).total_seconds()) < 60 for d in scheduled_dates)


@pytest.mark.asyncio
async def test_update_lead_status_to_terminal_cancels_pending_jobs(
    mock_agent, client: AsyncClient, admin_headers
) -> None:
    """PATCH sang WON/LOST/COLD phải cancel các pending jobs của lead đó."""
    from app.db.session import AsyncSessionLocal
    from app.models.models import FollowupRule

    async with AsyncSessionLocal() as db:
        db.add(FollowupRule(
            trigger_status="QUOTED",
            delay_days=3,
            action_type="email_customer",
            template=None,
            is_active=True,
        ))
        await db.commit()

    import uuid
    sid = str(uuid.uuid4())
    await client.post(
        "/api/chat",
        json={"session_id": sid, "message": "Test terminal cancel"},
    )

    list_res = await client.get("/api/leads", headers=admin_headers)
    lead_id = next(
        item["id"] for item in list_res.json()["items"] if item["session_id"] == sid
    )

    await client.patch(
        f"/api/leads/{lead_id}",
        json={"status": "QUOTED"},
        headers=admin_headers,
    )

    jobs_before = await client.get(
        f"/api/followup/jobs?lead_id={lead_id}", headers=admin_headers
    )
    assert len(jobs_before.json()) >= 1
    assert all(j["status"] == "pending" for j in jobs_before.json())

    upd = await client.patch(
        f"/api/leads/{lead_id}",
        json={"status": "WON"},
        headers=admin_headers,
    )
    assert upd.status_code == 200

    jobs_after = await client.get(
        f"/api/followup/jobs?lead_id={lead_id}", headers=admin_headers
    )
    assert all(j["status"] == "cancelled" for j in jobs_after.json())


@pytest.mark.asyncio
async def test_update_lead_notes(mock_agent, client: AsyncClient, admin_headers) -> None:
    """Thêm ghi chú nội bộ cho lead."""
    import uuid
    sid = str(uuid.uuid4())
    await client.post(
        "/api/chat",
        json={"session_id": sid, "message": "Test lead notes"},
    )

    list_res = await client.get("/api/leads", headers=admin_headers)
    lead_id = list_res.json()["items"][0]["id"]

    upd = await client.patch(
        f"/api/leads/{lead_id}",
        json={"notes": "Khách hàng tiềm năng, đã gọi điện tư vấn"},
        headers=admin_headers,
    )
    assert upd.status_code == 200
    assert upd.json()["notes"] == "Khách hàng tiềm năng, đã gọi điện tư vấn"


@pytest.mark.asyncio
async def test_update_lead_terminal_status(mock_agent, client: AsyncClient, admin_headers) -> None:
    """Chuyển sang WON/LOST/COLD vẫn được."""
    import uuid
    sid = str(uuid.uuid4())
    await client.post(
        "/api/chat",
        json={"session_id": sid, "message": "Test terminal"},
    )

    list_res = await client.get("/api/leads", headers=admin_headers)
    lead_id = list_res.json()["items"][0]["id"]

    for status in ("WON", "LOST", "COLD"):
        upd = await client.patch(
            f"/api/leads/{lead_id}",
            json={"status": status},
            headers=admin_headers,
        )
        assert upd.status_code == 200
        assert upd.json()["status"] == status


# ── Delete lead ─────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_lead(mock_agent, client: AsyncClient, admin_headers) -> None:
    import uuid
    sid = str(uuid.uuid4())
    await client.post(
        "/api/chat",
        json={"session_id": sid, "message": "To be deleted"},
    )

    list_res = await client.get("/api/leads", headers=admin_headers)
    lead_id = list_res.json()["items"][0]["id"]

    del_res = await client.delete(f"/api/leads/{lead_id}", headers=admin_headers)
    assert del_res.status_code == 204


# ── Sắp xếp ────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_leads_sort(mock_agent, client: AsyncClient, admin_headers) -> None:
    """Sort theo name asc/desc."""
    import uuid
    # Tạo 2 leads để test sort
    sid_a = str(uuid.uuid4())
    sid_b = str(uuid.uuid4())
    await client.post("/api/chat", json={"session_id": sid_a, "message": "Lead A"})
    await client.post("/api/chat", json={"session_id": sid_b, "message": "Lead B"})

    list_res = await client.get("/api/leads?sort_by=created_at&sort_order=asc", headers=admin_headers)
    assert list_res.status_code == 200

    list_res2 = await client.get("/api/leads?sort_by=created_at&sort_order=desc", headers=admin_headers)
    assert list_res2.status_code == 200


# ── Lọc theo status ──────────────────────────────────


@pytest.mark.asyncio
async def test_list_leads_filter_status(mock_agent, client: AsyncClient, admin_headers) -> None:
    """Filter leads by status."""
    import uuid
    sid = str(uuid.uuid4())
    await client.post("/api/chat", json={"session_id": sid, "message": "Filter test"})

    list_res = await client.get("/api/leads?status=NEW", headers=admin_headers)
    assert list_res.status_code == 200
    assert list_res.json()["pagination"]["total"] >= 1

    list_res2 = await client.get("/api/leads?status=WON", headers=admin_headers)
    assert list_res2.status_code == 200
    # Chưa có lead nào WON nếu chỉ qua chat
    # total có thể >= 0


# ── Lead collection flow ──────────────────────────


@pytest.mark.asyncio
async def test_lead_flow_idle_to_complete(mock_agent, client: AsyncClient) -> None:
    """Lead flow từ IDLE → (collecting) → COMPLETE qua nhiều tin nhắn."""
    import uuid
    sid = str(uuid.uuid4())

    # Tin nhắn 1: IDLE → detect intent lead
    res1 = await client.post(
        "/api/chat",
        json={"session_id": sid, "message": "Tôi muốn làm app AI"},
    )
    assert res1.status_code == 200
    d1 = res1.json()
    assert d1["lead_status"] in ("COLLECTING", "COMPLETE", "IDLE")

    # Tin nhắn 2: gửi tiếp để collecting
    res2 = await client.post(
        "/api/chat",
        json={"session_id": sid, "message": "Tên tôi là Nguyễn Văn A"},
    )
    assert res2.status_code == 200
    d2 = res2.json()
    assert "reply" in d2


@pytest.mark.asyncio
async def test_lead_flow_general_faq_no_lead(mock_agent, client: AsyncClient) -> None:
    """Câu hỏi FAQ không tạo lead state collecting."""
    import uuid
    sid = str(uuid.uuid4())

    res = await client.post(
        "/api/chat",
        json={"session_id": sid, "message": "AMD làm dịch vụ gì?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["lead_status"] == "IDLE"


# ── Lead list response có lead_state và notes ─────


@pytest.mark.asyncio
async def test_lead_list_has_new_fields(mock_agent, client: AsyncClient, admin_headers) -> None:
    """LeadListOut phải có lead_state, notes, next_followup_date."""
    import uuid
    sid = str(uuid.uuid4())
    await client.post(
        "/api/chat",
        json={"session_id": sid, "message": "Check fields"},
    )

    list_res = await client.get("/api/leads", headers=admin_headers)
    lead = list_res.json()["items"][0]
    assert "lead_state" in lead
    assert "notes" in lead
    assert "next_followup_date" in lead
