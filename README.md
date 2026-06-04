# AMD Chatbot — Backend

> **Intern A** — Backend API, AI Pipeline, Follow-up Engine  
> Stack: Python 3.11 · FastAPI · OpenAI · ChromaDB · SQLite · APScheduler · SendGrid

---

## Cấu trúc thư mục

```
backend/
├── app/
│   ├── main.py                  # FastAPI app, routers, lifecycle
│   ├── api/routes/
│   │   ├── chat.py              # POST /api/chat
│   │   ├── leads.py             # GET/PATCH /api/leads
│   │   ├── documents.py         # POST/DELETE /api/documents
│   │   ├── followup.py          # /api/followup/rules + /jobs
│   │   └── settings.py          # /api/settings
│   ├── agent/
│   │   └── chat_agent.py        # RAG + Intent + Lead State Machine
│   ├── rag/
│   │   └── pipeline.py          # Ingest, chunk, embed, query
│   ├── scheduler/
│   │   └── followup_scheduler.py # APScheduler jobs
│   ├── services/email/
│   │   └── email_service.py     # SendGrid + Jinja2 templates
│   ├── models/
│   │   └── models.py            # SQLAlchemy ORM
│   ├── schemas/
│   │   └── schemas.py           # Pydantic request/response
│   ├── core/
│   │   ├── config.py            # Pydantic Settings (.env)
│   │   └── security.py          # JWT auth + dependency
│   └── db/
│       └── session.py           # Async engine + session factory
├── tests/
│   ├── unit/test_intent/        # 20 test cases intent detection
│   └── integration/             # End-to-end API tests
├── scripts/
│   └── seed_db.py               # Seed DB với default rules + settings
├── data/
│   ├── knowledge_base/          # Files upload
│   └── chroma_db/               # ChromaDB persistent storage
├── docs/
│   └── api_contract.md          # API contract cho Intern B
├── pyproject.toml
└── .env.example
```

---

## Setup local

### 1. Cài đặt dependencies

```bash
# Dùng uv (khuyến nghị)
uv sync --extra dev

# Hoặc pip
pip install -e ".[dev]"
```

### 2. Tạo file .env

```bash
cp .env.example .env
# Điền OPENAI_API_KEY, JWT_SECRET_KEY, SENDGRID_API_KEY
```

Tạo `JWT_SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Khởi tạo & seed database

```bash
python scripts/seed_db.py
```

### 4. Chạy server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

---

## Chạy tests

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## API Endpoints tóm tắt

| Method | Path | Auth | Mô tả |
|--------|------|------|-------|
| POST | /api/auth/login | ❌ | Đăng nhập, nhận JWT |
| POST | /api/chat | ❌ | Widget gửi tin nhắn |
| GET | /api/leads | ✅ JWT | Danh sách leads |
| GET | /api/leads/{id} | ✅ JWT | Chi tiết lead + chat log |
| PATCH | /api/leads/{id} | ✅ JWT | Cập nhật status, notes |
| GET | /api/documents | ✅ JWT | Danh sách tài liệu KB |
| POST | /api/documents | ✅ JWT | Upload tài liệu |
| DELETE | /api/documents/{id} | ✅ JWT | Xóa tài liệu |
| POST | /api/documents/{id}/reindex | ✅ JWT | Re-embed tài liệu |
| GET | /api/followup/rules | ✅ JWT | Danh sách rules |
| POST | /api/followup/rules | ✅ JWT | Tạo rule mới |
| PATCH | /api/followup/rules/{id} | ✅ JWT | Sửa rule |
| DELETE | /api/followup/rules/{id} | ✅ JWT | Xóa rule |
| GET | /api/followup/jobs | ✅ JWT | Xem jobs |
| POST | /api/followup/jobs/{id}/cancel | ✅ JWT | Cancel job |
| GET | /api/settings | ✅ JWT | Tất cả settings |
| PUT | /api/settings/{key} | ✅ JWT | Upsert setting |
| GET | /health | ❌ | Health check |

---

## Lead Status Flow

```
NEW → CONTACTED → CONSULTING → QUOTED → NEGOTIATING → WON / LOST / COLD
```

Khi status thay đổi → scheduler tự tạo follow-up jobs theo rules.

---

## Sync với Intern B

- **API contract**: Xem `docs/api_contract.md`
- **Tuần 1**: Pair programming, align schemas
- **Tuần 2+**: Intern B gọi API qua `http://localhost:8000`
- **CORS**: Đã cấu hình cho `http://localhost:5173` (Vite dev server)
