"""
SQLAlchemy ORM models — ánh xạ 1-1 với schema trong spec.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


# ─────────────────────────────────────────────
# Leads
# ─────────────────────────────────────────────
class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(Text)
    contact: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="NEW")

    # Flexible fields AI thu thập — lưu dạng JSON string
    _fields: Mapped[str | None] = mapped_column("fields", Text, default="{}")
    # Toàn bộ hội thoại — lưu dạng JSON string
    _chat_log: Mapped[str | None] = mapped_column("chat_log", Text, default="[]")

    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    followup_jobs: Mapped[list[FollowupJob]] = relationship(
        "FollowupJob", back_populates="lead", cascade="all, delete-orphan"
    )

    @property
    def fields(self) -> dict[str, Any]:
        return json.loads(self._fields or "{}")

    @fields.setter
    def fields(self, value: dict[str, Any]) -> None:
        self._fields = json.dumps(value, ensure_ascii=False)

    @property
    def chat_log(self) -> list[dict]:
        return json.loads(self._chat_log or "[]")

    @chat_log.setter
    def chat_log(self, value: list[dict]) -> None:
        self._chat_log = json.dumps(value, ensure_ascii=False)


# ─────────────────────────────────────────────
# Follow-up Rules (cấu hình trong Settings)
# ─────────────────────────────────────────────
class FollowupRule(Base):
    __tablename__ = "followup_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trigger_status: Mapped[str] = mapped_column(Text)       # 'QUOTED', 'NEW', 'COLD', ...
    delay_days: Mapped[int] = mapped_column(Integer)
    action_type: Mapped[str] = mapped_column(Text)          # 'email_customer' | 'email_internal'
    template: Mapped[str | None] = mapped_column(Text)      # Jinja2 template string
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    jobs: Mapped[list[FollowupJob]] = relationship("FollowupJob", back_populates="rule")


# ─────────────────────────────────────────────
# Follow-up Jobs (thực thi thực tế)
# ─────────────────────────────────────────────
class FollowupJob(Base):
    __tablename__ = "followup_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"))
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("followup_rules.id", ondelete="SET NULL"))
    scheduled: Mapped[datetime] = mapped_column(DateTime)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(Text, default="pending")  # pending | sent | cancelled
    result_note: Mapped[str | None] = mapped_column(Text)

    lead: Mapped[Lead] = relationship("Lead", back_populates="followup_jobs")
    rule: Mapped[FollowupRule | None] = relationship("FollowupRule", back_populates="jobs")


# ─────────────────────────────────────────────
# Settings (key-value, JSON value)
# ─────────────────────────────────────────────
class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    _value: Mapped[str | None] = mapped_column("value", Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    @property
    def value(self) -> Any:
        return json.loads(self._value or "null")

    @value.setter
    def value(self, v: Any) -> None:
        self._value = json.dumps(v, ensure_ascii=False)


# ─────────────────────────────────────────────
# Knowledge Base Documents
# ─────────────────────────────────────────────
class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="indexing")  # indexing | ready | error
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
