import time
from collections import defaultdict

from fastapi import HTTPException


class _SlidingWindowLimiter:
    def __init__(self):
        self._windows: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, max_reqs: int = 30, window: int = 60) -> None:
        now = time.time()
        window_entries = self._windows[key]
        self._windows[key] = [t for t in window_entries if now - t < window]
        if len(self._windows[key]) >= max_reqs:
            raise HTTPException(
                status_code=429,
                detail=f"Vượt quá {max_reqs} requests/{window}s. Vui lòng thử lại sau.",
            )
        self._windows[key].append(now)


chat_rate_limiter = _SlidingWindowLimiter()
