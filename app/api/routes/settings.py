"""
/api/settings — Key-value store cho toàn bộ cấu hình hệ thống.
Thay đổi runtime không cần restart.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin
from app.db.session import get_db
from app.models.models import Setting
from app.schemas.schemas import SettingOut, SettingUpsert
from app.services.settings_service import settings_service

router = APIRouter(prefix="/api/settings", tags=["Settings"])


@router.get("", response_model=list[SettingOut])
async def get_all_settings(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
) -> list[SettingOut]:
    result = await db.execute(select(Setting))
    return result.scalars().all()


@router.get("/{key}", response_model=SettingOut)
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
) -> SettingOut:
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(404, f"Setting '{key}' not found")
    return setting


@router.put("/{key}", response_model=SettingOut)
async def upsert_setting(
    key: str,
    body: SettingUpsert,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
) -> SettingOut:
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()

    if setting:
        setting.value = body.value
    else:
        setting = Setting(key=key)
        setting.value = body.value
        db.add(setting)

    settings_service.invalidate()
    await db.commit()
    await db.refresh(setting)
    return setting


@router.delete("/{key}", status_code=204)
async def delete_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
) -> None:
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(404, f"Setting '{key}' not found")
    settings_service.invalidate()
    await db.delete(setting)
    await db.commit()
