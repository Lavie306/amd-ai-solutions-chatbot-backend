"""
POST /api/chat — Endpoint chính cho widget gửi tin nhắn.

Flow:
  1. Tìm/tạo session lead trong DB
  2. Gọi chat_agent.handle_chat()
  3. Nếu lead vừa COMPLETE → save lead + gửi email notify async
  4. Trả về reply
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.chat_agent import handle_chat
from app.core.rate_limit import chat_rate_limiter
from app.db.session import get_db
from app.models.models import Lead
from app.schemas.schemas import ChatRequest, ChatResponse
from app.services.email.email_service import async_send_lead_notify
from app.services.settings_service import settings_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Chat"])


_DEFAULT_FIELDS = [
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
    chat_rate_limiter.check(req.session_id)

    result = await db.execute(select(Lead).where(Lead.session_id == req.session_id))
    lead = result.scalar_one_or_none()

    if not lead:
        lead = Lead(session_id=req.session_id)
        db.add(lead)
        await db.flush()

    settings_dict = await settings_service.get_all(db)
    available_fields = settings_dict.get("lead_fields") or _DEFAULT_FIELDS

    prev_lead_state = lead.lead_state

    agent_result = await handle_chat(
        session_id=req.session_id,
        user_message=req.message,
        chat_history=lead.chat_log,
        lead_state=prev_lead_state,
        collected_fields=lead.fields,
        available_fields=available_fields,
        settings_dict=settings_dict,
    )

    new_lead_state = agent_result.get("lead_state", "IDLE")
    lead.lead_state = new_lead_state

    log = lead.chat_log
    log.append({"role": "user", "content": req.message})
    log.append({"role": "assistant", "content": agent_result["reply"]})
    lead.chat_log = log

    if agent_result.get("collected_fields"):
        fields = agent_result["collected_fields"]
        lead.fields = fields
        lead.name = fields.get("name") or lead.name
        lead.contact = fields.get("contact") or lead.contact

    if new_lead_state == "COMPLETE" and prev_lead_state != "COMPLETE":
        lead.status = "NEW"
        try:
            await async_send_lead_notify(
                lead_id=lead.id,
                name=lead.name or "",
                contact=lead.contact or "",
                extra_fields={
                    k: v
                    for k, v in lead.fields.items()
                    if k not in ("name", "contact")
                },
                chat_log=lead.chat_log,
            )
        except Exception as e:
            logger.error("Email notify failed: %s", e)

    await db.commit()

    return ChatResponse(
        session_id=req.session_id,
        reply=agent_result["reply"],
        intent=agent_result.get("intent"),
        lead_status=new_lead_state,
    )
