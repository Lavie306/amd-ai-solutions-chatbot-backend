"""
POST /api/chat — Endpoint chính cho widget gửi tin nhắn.

Flow:
  1. Tìm/tạo session lead trong DB
  2. Gọi chat_agent.handle_chat()
  3. Nếu lead vừa COMPLETE → save lead + gửi email notify
  4. Trả về reply
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.chat_agent import LeadState, handle_chat
from app.db.session import get_db
from app.models.models import Lead, Setting
from app.schemas.schemas import ChatRequest, ChatResponse
from app.services.email.email_service import send_lead_notify

router = APIRouter(prefix="/api/chat", tags=["Chat"])


async def _get_settings_dict(db: AsyncSession) -> dict:
    """Lấy toàn bộ settings từ DB dưới dạng dict."""
    result = await db.execute(select(Setting))
    settings_rows = result.scalars().all()
    return {row.key: row.value for row in settings_rows}


async def _get_available_fields(db: AsyncSession) -> list[dict]:
    """Lấy danh sách lead fields từ Settings."""
    result = await db.execute(select(Setting).where(Setting.key == "lead_fields"))
    row = result.scalar_one_or_none()
    if row and row.value:
        return row.value
    # Default fields nếu chưa cấu hình
    return [
        {"key": "name", "label": "Tên liên hệ", "required": True, "enabled": True},
        {"key": "contact", "label": "SĐT hoặc email", "required": True, "enabled": True},
        {"key": "project_type", "label": "Loại dự án", "required": False, "enabled": True},
        {"key": "scale", "label": "Quy mô / số user", "required": False, "enabled": True},
        {"key": "timeline", "label": "Dự kiến triển khai", "required": False, "enabled": True},
        {"key": "budget_range", "label": "Ngân sách ước tính", "required": False, "enabled": True},
        {"key": "current_problem", "label": "Vấn đề đang gặp", "required": False, "enabled": True},
    ]


@router.post("", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    # ── 1. Tìm hoặc tạo lead session ──
    result = await db.execute(select(Lead).where(Lead.session_id == req.session_id))
    lead = result.scalar_one_or_none()

    if not lead:
        lead = Lead(session_id=req.session_id)
        db.add(lead)
        await db.flush()

    # ── 2. Lấy settings & fields ──
    settings_dict = await _get_settings_dict(db)
    available_fields = await _get_available_fields(db)

    # ── 3. Gọi agent ──
    agent_result = await handle_chat(
        session_id=req.session_id,
        user_message=req.message,
        chat_history=lead.chat_log,
        lead_state=lead.status if lead.status in ("IDLE", "COLLECTING", "COMPLETE") else "IDLE",
        collected_fields=lead.fields,
        available_fields=available_fields,
        settings_dict=settings_dict,
    )

    # ── 4. Cập nhật chat log ──
    log = lead.chat_log
    log.append({"role": "user", "content": req.message})
    log.append({"role": "assistant", "content": agent_result["reply"]})
    lead.chat_log = log

    # ── 5. Cập nhật collected fields ──
    if agent_result.get("collected_fields"):
        fields = agent_result["collected_fields"]
        lead.fields = fields
        lead.name = fields.get("name") or lead.name
        lead.contact = fields.get("contact") or lead.contact

    # ── 6. Xử lý khi lead COMPLETE ──
    lead_state_str = agent_result.get("lead_state", "IDLE")
    was_complete = lead.status == "COMPLETE"

    if lead_state_str == "COMPLETE" and not was_complete:
        lead.status = "NEW"  # Chuyển về NEW (CRM status), không phải collection state

        # Gửi email notify AMD
        try:
            send_lead_notify(
                lead_id=lead.id,
                name=lead.name or "",
                contact=lead.contact or "",
                extra_fields={k: v for k, v in lead.fields.items() if k not in ("name", "contact")},
                chat_log=lead.chat_log,
            )
        except Exception as e:
            # Email lỗi không nên crash chat
            import logging
            logging.getLogger(__name__).error(f"Email notify failed: {e}")

    await db.commit()

    return ChatResponse(
        session_id=req.session_id,
        reply=agent_result["reply"],
        intent=agent_result.get("intent"),
        lead_status=lead_state_str,
    )
