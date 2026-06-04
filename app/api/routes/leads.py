"""
/api/leads — CRUD leads + status transitions + follow-up trigger.
"""
from __future__ import annotations

import math
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.security import require_admin
from app.db.session import get_db
from app.models.models import FollowupJob, Lead
from app.schemas.schemas import LeadListOut, LeadOut, LeadUpdate, PaginatedLeadList
from app.scheduler.followup_scheduler import cancel_followup_jobs, schedule_followup_jobs

router = APIRouter(prefix="/api/leads", tags=["Leads"])

TERMINAL_STATUSES = {"WON", "LOST", "COLD"}
SORTABLE_COLUMNS = {
    "created_at": Lead.created_at,
    "updated_at": Lead.updated_at,
    "name": Lead.name,
    "status": Lead.status,
}


@router.get("", response_model=PaginatedLeadList)
async def list_leads(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at", pattern="^(created_at|updated_at|name|status)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
) -> PaginatedLeadList:
    order_col = SORTABLE_COLUMNS.get(sort_by, Lead.created_at)
    order = order_col.desc() if sort_order == "desc" else order_col.asc()

    count_query = select(func.count(Lead.id))
    if status:
        count_query = count_query.where(Lead.status == status)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = (
        select(Lead)
        .options(joinedload(Lead.followup_jobs))
        .order_by(order)
    )
    if status:
        query = query.where(Lead.status == status)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)

    leads = result.unique().scalars().all()
    items: list[LeadListOut] = []
    for lead in leads:
        next_followup: datetime | None = None
        for job in lead.followup_jobs:
            if job.status == "pending" and job.scheduled:
                if next_followup is None or job.scheduled < next_followup:
                    next_followup = job.scheduled
        items.append(LeadListOut(
            id=lead.id,
            session_id=lead.session_id,
            name=lead.name,
            contact=lead.contact,
            status=lead.status,
            lead_state=lead.lead_state,
            fields=lead.fields,
            notes=lead.notes,
            created_at=lead.created_at,
            next_followup_date=next_followup,
        ))

    return PaginatedLeadList(
        items=items,
        pagination={
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, math.ceil(total / page_size)),
        },
    )


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
