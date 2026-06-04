"""
/api/followup — Xem jobs, CRUD rules, cancel job thủ công.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin
from app.db.session import get_db
from app.models.models import FollowupJob, FollowupRule
from app.schemas.schemas import (
    FollowupJobOut,
    FollowupRuleCreate,
    FollowupRuleOut,
    FollowupRuleUpdate,
)

router = APIRouter(prefix="/api/followup", tags=["Follow-up"])


# ── Rules ──────────────────────────────────────
@router.get("/rules", response_model=list[FollowupRuleOut])
async def list_rules(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
) -> list[FollowupRuleOut]:
    result = await db.execute(select(FollowupRule).order_by(FollowupRule.id))
    return result.scalars().all()


@router.post("/rules", response_model=FollowupRuleOut, status_code=201)
async def create_rule(
    body: FollowupRuleCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
) -> FollowupRuleOut:
    rule = FollowupRule(**body.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.patch("/rules/{rule_id}", response_model=FollowupRuleOut)
async def update_rule(
    rule_id: int,
    body: FollowupRuleUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
) -> FollowupRuleOut:
    result = await db.execute(select(FollowupRule).where(FollowupRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Rule not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
) -> None:
    result = await db.execute(select(FollowupRule).where(FollowupRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Rule not found")
    await db.delete(rule)
    await db.commit()


# ── Jobs ──────────────────────────────────────
@router.get("/jobs", response_model=list[FollowupJobOut])
async def list_jobs(
    lead_id: int | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
) -> list[FollowupJobOut]:
    query = select(FollowupJob).order_by(FollowupJob.scheduled.desc())
    if lead_id:
        query = query.where(FollowupJob.lead_id == lead_id)
    if status:
        query = query.where(FollowupJob.status == status)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/jobs/{job_id}/cancel", response_model=FollowupJobOut)
async def cancel_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
) -> FollowupJobOut:
    from app.scheduler.followup_scheduler import scheduler

    result = await db.execute(select(FollowupJob).where(FollowupJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != "pending":
        raise HTTPException(400, f"Job status is '{job.status}', cannot cancel")

    apscheduler_id = f"followup_{job_id}"
    if scheduler.get_job(apscheduler_id):
        scheduler.remove_job(apscheduler_id)

    job.status = "cancelled"
    await db.commit()
    await db.refresh(job)
    return job
