"""
conftest cho integration tests — quản lý test database lifecycle.
"""
from pathlib import Path

import pytest

from app.db.session import init_db


@pytest.fixture(autouse=True, scope="session")
async def _setup_test_db():
    """Xoá test DB cũ, tạo tables mới trước khi chạy integration tests."""
    db_path = Path(__file__).parent.parent.parent / "data" / "test_amd_chatbot.db"
    if db_path.exists():
        db_path.unlink()
    await init_db()
    yield
    try:
        if db_path.exists():
            db_path.unlink(missing_ok=True)
    except PermissionError:
        pass  # SQLAlchemy engine still holds handle, ignore