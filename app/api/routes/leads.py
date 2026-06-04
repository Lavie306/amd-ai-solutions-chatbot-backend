"""
/api/leads — CRUD leads + status transitions + follow-up trigger.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin
from app.db.session import get_db
from app.models.models import Lead
from app.schemas.schemas import LeadListOut, LeadOut, LeadUpdate
from app.scheduler.followup_scheduler import cancel_followup_jobs, schedule_followup_jobs

router = APIRouter(prefix="/api/leads", tags=["Leads"])

TERMINAL_STATUSES = {"WON", "LOST", "COLD"}


@router.get("", response_model=list[LeadListOut])
async def list_leads(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
) -> list[LeadListOut]:
    query = select(Lead).order_by(Lead.created_at.desc())
    if status:
        query = query.where(Lead.status == status)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{lead_id}", response_model=LeadOut)
async def get_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
) -> LeadOut:
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.patch("/{lead_id}", response_model=LeadOut)
async def update_lead(
    lead_id: int,
    body: LeadUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
) -> LeadOut:
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    old_status = lead.status

    if body.status and body.status != old_status:
        lead.status = body.status

        # Nếu vào terminal status → cancel pending follow-ups
        if body.status in TERMINAL_STATUSES:
            await cancel_followup_jobs(lead_id, db)
        else:
            # Tạo follow-up jobs theo rule mới
            await schedule_followup_jobs(
                lead_id=lead_id,
                new_status=body.status,
                lead_data={
                    "id": lead.id,
                    "name": lead.name,
                    "contact": lead.contact,
                    "project_type": lead.fields.get("project_type", ""),
                    **lead.fields,
                },
                db=db,
            )

    if body.notes is not None:
        lead.notes = body.notes

    await db.commit()
    await db.refresh(lead)
    return lead


@router.delete("/{lead_id}", status_code=204)
async def delete_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
) -> None:
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    await cancel_followup_jobs(lead_id, db)
    await db.delete(lead)
    await db.commit()
