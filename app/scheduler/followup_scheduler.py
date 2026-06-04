"""
Follow-up Scheduler — APScheduler chạy background jobs.

Logic:
  - Khi lead.status thay đổi → tự tạo FollowupJob theo rules
  - Job chạy đúng thời điểm scheduled → gửi email → cập nhật status
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Singleton scheduler
scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started")


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")


# ─────────────────────────────────────────────
# Tạo follow-up jobs khi lead đổi trạng thái
# ─────────────────────────────────────────────
async def schedule_followup_jobs(
    lead_id: int,
    new_status: str,
    lead_data: dict[str, Any],
    db: AsyncSession,
) -> int:
    """
    Tìm tất cả rule active với trigger_status == new_status,
    tạo FollowupJob tương ứng và đăng ký vào scheduler.
    Trả về số job được tạo.
    """
    from sqlalchemy import select

    from app.models.models import FollowupJob, FollowupRule

    result = await db.execute(
        select(FollowupRule).where(
            FollowupRule.trigger_status == new_status,
            FollowupRule.is_active == True,  # noqa: E712
        )
    )
    rules = result.scalars().all()

    count = 0
    for rule in rules:
        run_at = datetime.now() + timedelta(days=rule.delay_days)

        job = FollowupJob(
            lead_id=lead_id,
            rule_id=rule.id,
            scheduled=run_at,
            status="pending",
        )
        db.add(job)
        await db.flush()  # Lấy job.id

        # Đăng ký APScheduler job
        scheduler.add_job(
            _execute_followup_job,
            trigger=DateTrigger(run_date=run_at, timezone=settings.scheduler_timezone),
            args=[job.id, lead_data, rule.action_type, rule.template],
            id=f"followup_{job.id}",
            replace_existing=True,
        )
        logger.info(f"Scheduled followup job {job.id} for lead {lead_id} at {run_at}")
        count += 1

    await db.commit()
    return count


async def cancel_followup_jobs(lead_id: int, db: AsyncSession) -> None:
    """Hủy tất cả pending jobs của một lead (ví dụ: khi lead WON/LOST)."""
    from sqlalchemy import select, update

    from app.models.models import FollowupJob

    result = await db.execute(
        select(FollowupJob).where(
            FollowupJob.lead_id == lead_id,
            FollowupJob.status == "pending",
        )
    )
    jobs = result.scalars().all()

    for job in jobs:
        job_id = f"followup_{job.id}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
        job.status = "cancelled"

    await db.commit()


# ─────────────────────────────────────────────
# Thực thi follow-up job
# ─────────────────────────────────────────────
async def _execute_followup_job(
    job_id: int,
    lead_data: dict[str, Any],
    action_type: str,
    template: str | None,
) -> None:
    """Được gọi bởi APScheduler khi đến giờ."""
    from app.db.session import AsyncSessionLocal
    from app.models.models import FollowupJob, Setting
    from app.services.email.email_service import send_followup_email, send_email
    from sqlalchemy import select

    logger.info(f"Executing followup job {job_id}")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(FollowupJob).where(FollowupJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job or job.status != "pending":
            logger.warning(f"Job {job_id} not found or not pending, skipping")
            return

        # Lấy zalo_number từ Settings
        zalo_result = await db.execute(select(Setting).where(Setting.key == "chatbot.zalo_number"))
        zalo_setting = zalo_result.scalar_one_or_none()
        zalo_number = zalo_setting.value if zalo_setting else ""

        success = False
        if action_type == "email_customer":
            to_email = lead_data.get("contact", "")
            if "@" in to_email:
                success = send_followup_email(
                    to_email=to_email,
                    lead_data=lead_data,
                    template_str=template,
                    zalo_number=zalo_number,
                )
        elif action_type == "email_internal":
            from app.core.config import get_settings as gs
            s = gs()
            success = send_email(
                to_email=s.email_notify_to,
                subject=f"[AMD Nhắc] Lead #{lead_data.get('id')} — {lead_data.get('name')}",
                body_html=template or f"Nhắc xử lý lead: {lead_data}",
            )

        job.status = "sent" if success else "pending"
        job.sent_at = datetime.now()
        job.result_note = "Sent successfully" if success else "Send failed — will retry"
        await db.commit()

        logger.info(f"Job {job_id} completed with success={success}")
