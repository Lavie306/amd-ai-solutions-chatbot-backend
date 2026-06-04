"""
Script seed dữ liệu ban đầu:
- Default follow-up rules từ spec
- Default settings
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import AsyncSessionLocal, init_db
from app.models.models import FollowupRule, Setting


DEFAULT_RULES = [
    {
        "trigger_status": "NEW",
        "delay_days": 1,
        "action_type": "email_internal",
        "template": "Nhắc: Lead #{{lead_id}} ({{name}}) chưa được liên hệ sau 1 ngày.",
        "is_active": True,
    },
    {
        "trigger_status": "QUOTED",
        "delay_days": 3,
        "action_type": "email_customer",
        "template": None,  # Dùng DEFAULT_FOLLOWUP_HTML
        "is_active": True,
    },
    {
        "trigger_status": "QUOTED",
        "delay_days": 7,
        "action_type": "email_customer",
        "template": None,
        "is_active": True,
    },
    {
        "trigger_status": "CONSULTING",
        "delay_days": 5,
        "action_type": "email_internal",
        "template": "Nhắc: Lead {{name}} đang CONSULTING 5 ngày, hỏi lại kết quả.",
        "is_active": True,
    },
    {
        "trigger_status": "COLD",
        "delay_days": 14,
        "action_type": "email_customer",
        "template": None,
        "is_active": True,
    },
]

DEFAULT_SETTINGS = {
    "bot_name": "AMD Assistant",
    "welcome_message": "Xin chào! Tôi là trợ lý ảo của AMD AI Solutions. Tôi có thể giúp gì cho bạn?",
    "handoff_message": "Cảm ơn bạn đã để lại thông tin. Team AMD sẽ liên hệ trong vòng 24h làm việc.",
    "chatbot.zalo_number": "0901 234 567",
    "chatbot.language": "vi",
    "email_notification.enabled": True,
    "lead_fields": [
        {"key": "name", "label": "Tên liên hệ", "required": True, "enabled": True},
        {"key": "contact", "label": "SĐT hoặc email", "required": True, "enabled": True},
        {"key": "project_type", "label": "Loại dự án", "required": False, "enabled": True},
        {"key": "scale", "label": "Quy mô / số user", "required": False, "enabled": True},
        {"key": "timeline", "label": "Dự kiến triển khai", "required": False, "enabled": True},
        {"key": "budget_range", "label": "Ngân sách ước tính", "required": False, "enabled": True},
        {"key": "current_problem", "label": "Vấn đề đang gặp", "required": False, "enabled": True},
        {"key": "note", "label": "Ghi chú thêm", "required": False, "enabled": True},
    ],
}


async def seed() -> None:
    await init_db()
    async with AsyncSessionLocal() as db:
        # Seed follow-up rules
        from sqlalchemy import select
        existing = await db.execute(select(FollowupRule))
        if not existing.scalars().first():
            for rule_data in DEFAULT_RULES:
                db.add(FollowupRule(**rule_data))
            print(f"Seeded {len(DEFAULT_RULES)} follow-up rules")
        else:
            print("Follow-up rules already exist, skipping")

        # Seed settings
        for key, value in DEFAULT_SETTINGS.items():
            result = await db.execute(select(Setting).where(Setting.key == key))
            if not result.scalar_one_or_none():
                s = Setting(key=key)
                s.value = value
                db.add(s)
        print("Seeded settings")

        await db.commit()
        print("Seed complete!")


if __name__ == "__main__":
    asyncio.run(seed())
