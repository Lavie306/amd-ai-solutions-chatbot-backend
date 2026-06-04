"""
Pydantic schemas cho request/response — API contract với Intern B.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# Chat
# ─────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="UUID do widget tạo, duy trì xuyên suốt cuộc hội thoại")
    message: str = Field(..., max_length=2000)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    intent: str | None = None           # intent được detect (nếu có)
    lead_status: str | None = None      # trạng thái collect lead hiện tại


# ─────────────────────────────────────────────
# Lead
# ─────────────────────────────────────────────
class LeadBase(BaseModel):
    name: str | None = None
    contact: str | None = None
    status: str = "NEW"
    fields: dict[str, Any] = {}
    notes: str | None = None


class LeadCreate(LeadBase):
    session_id: str


class LeadUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None


class LeadOut(LeadBase):
    id: int
    session_id: str
    lead_state: str = "IDLE"
    chat_log: list[dict]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadListOut(BaseModel):
    id: int
    session_id: str
    name: str | None
    contact: str | None
    status: str
    lead_state: str = "IDLE"
    fields: dict[str, Any]
    notes: str | None = None
    created_at: datetime
    next_followup_date: datetime | None = None

    model_config = {"from_attributes": True}


class PaginationMeta(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedLeadList(BaseModel):
    items: list[LeadListOut]
    pagination: PaginationMeta


# ─────────────────────────────────────────────
# Follow-up Rule
# ─────────────────────────────────────────────
class FollowupRuleBase(BaseModel):
    trigger_status: str
    delay_days: int = Field(..., ge=0)
    action_type: Literal["email_customer", "email_internal"]
    template: str | None = None
    is_active: bool = True


class FollowupRuleCreate(FollowupRuleBase):
    pass


class FollowupRuleUpdate(BaseModel):
    trigger_status: str | None = None
    delay_days: int | None = None
    action_type: str | None = None
    template: str | None = None
    is_active: bool | None = None


class FollowupRuleOut(FollowupRuleBase):
    id: int

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Follow-up Job
# ─────────────────────────────────────────────
class FollowupJobOut(BaseModel):
    id: int
    lead_id: int
    rule_id: int | None
    scheduled: datetime
    sent_at: datetime | None
    status: str
    result_note: str | None

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Settings
# ─────────────────────────────────────────────
class SettingOut(BaseModel):
    key: str
    value: Any
    updated_at: datetime

    model_config = {"from_attributes": True}


class SettingUpsert(BaseModel):
    value: Any


# ─────────────────────────────────────────────
# Document (Knowledge Base)
# ─────────────────────────────────────────────
class DocumentOut(BaseModel):
    id: int
    filename: str
    status: str
    chunk_count: int
    uploaded_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
