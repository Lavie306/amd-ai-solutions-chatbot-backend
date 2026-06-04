import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Setting


class SettingsService:
    def __init__(self, ttl: int = 10):
        self._cache: dict[str, Any] = {}
        self._last_fetch: float = 0
        self._ttl = ttl

    async def get_all(self, db: AsyncSession) -> dict[str, Any]:
        now = time.time()
        if now - self._last_fetch < self._ttl and self._cache:
            return self._cache
        result = await db.execute(select(Setting))
        rows = result.scalars().all()
        self._cache = {row.key: row.value for row in rows}
        self._last_fetch = now
        return self._cache

    def invalidate(self) -> None:
        self._cache = {}
        self._last_fetch = 0


settings_service = SettingsService()
