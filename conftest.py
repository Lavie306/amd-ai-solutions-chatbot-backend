"""
pytest conftest — cấu hình test environment.
"""
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

# Đảm bảo `app` import được từ thư mục backend
sys.path.insert(0, str(Path(__file__).parent))

# Dummy env vars cho test (không cần key thật)
import os
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy-key-for-pytest")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-not-real")
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./data/test_amd_chatbot.db"

# ── Mock heavy optional packages ──────────────────────────
# Để unit test chạy được khi chromadb/langchain chưa install

def _make_mock_module(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__spec__ = None  # type: ignore
    return mod

_HEAVY_PACKAGES = [
    "chromadb",
    "langchain",
    "langchain_chroma",
    "langchain_openai",
    "langchain_community",
    "langchain_community.document_loaders",
    "langchain_core",
    "langchain_core.documents",
    "langchain.text_splitter",
    "pypdf",
    "docx",
    "unstructured",
    "sendgrid",
    "sendgrid.helpers",
    "sendgrid.helpers.mail",
]

for _pkg in _HEAVY_PACKAGES:
    try:
        # Thử import gói thật xem có sẵn trong env không
        # Nếu import thành công, python tự động điền sys.modules[_pkg] bằng gói thật
        __import__(_pkg)
    except (ImportError, ModuleNotFoundError):
        if _pkg not in sys.modules:
            _mock = _make_mock_module(_pkg)
            # Thêm các attribute thường dùng
            _mock.Chroma = MagicMock()
            _mock.OpenAIEmbeddings = MagicMock()
            _mock.RecursiveCharacterTextSplitter = MagicMock()
            _mock.Document = MagicMock()
            _mock.PyPDFLoader = MagicMock()
            _mock.TextLoader = MagicMock()
            _mock.UnstructuredWordDocumentLoader = MagicMock()
            _mock.SendGridAPIClient = MagicMock()
            _mock.Mail = MagicMock()
            sys.modules[_pkg] = _mock




