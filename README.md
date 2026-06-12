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

### 3. Khởi tạo & seed database & nạp tri thức RAG

Khởi tạo cơ sở dữ liệu SQLite, tạo dữ liệu cấu hình ban đầu và nạp tài liệu FAQ vào cơ sở dữ liệu Vector (ChromaDB) để phục vụ tính năng RAG Chatbot:

```bash
# Khởi tạo DB, tạo settings mặc định và quy tắc follow-up
python scripts/seed_db.py

# Nạp tài liệu FAQ mặc định của AMD vào Vector Database (ChromaDB)
python scripts/ingest_default_kb.py
```

*Tài khoản Admin mặc định để đăng nhập Dashboard (Được cấu hình trong `.env`):*
*   **Email**: `admin@amd.vn`
*   **Password**: `changeme123`

### 4. Chạy server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```


API docs: http://localhost:8000/docs

---

## Chạy tests

Chạy test suite bằng `pytest`. Trên môi trường Windows, để tránh lỗi phân quyền (`PermissionError`) khi ghi đè hoặc truy cập các thư mục tạm trong lúc chạy test song song, vui lòng sử dụng cờ `--basetemp`:

```bash
python -m pytest tests/ -v --cov=app --cov-report=term-missing --basetemp=temp_pytest
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
| GET | /api/settings/public/config | ❌ | Lấy cấu hình widget công khai |
| GET | /health | ❌ | Health check |

---

## Nhúng Chatbot Widget vào Website

Để nhúng Chatbot Widget trực tiếp vào trang web HTML của bạn, chèn đoạn mã sau vào trước thẻ đóng `</body>`:

```html
<!-- Chatbot Widget Embed -->
<div id="amd-chatbot-root"></div>
<script 
  src="http://localhost:8000/static/chatbot-widget.js" 
  data-api-url="http://localhost:8000"
  defer>
</script>
```

Cấu hình widget (như tên chatbot, câu chào mừng, nút Zalo handoff) có thể được tùy biến động từ Admin Dashboard. Widget sẽ tự động gọi API công khai `/api/settings/public/config` để lấy cấu hình mới mà không yêu cầu thay đổi mã nhúng HTML.

*   Trang demo nhúng widget có sẵn tại: [static/demo.html](file:///d:/AI-AMD/backend/static/demo.html)
*   Trang xem thử dành cho Admin tại: [static/preview.html](file:///d:/AI-AMD/backend/static/preview.html)

---

## Hướng Dẫn Deploy lên Cloud (Render/Railway)

Ứng dụng FastAPI sử dụng cơ sở dữ liệu SQLite (`data/amd_chatbot.db`) và vector database ChromaDB (`data/chroma_db`). Khi deploy lên các dịch vụ đám mây (Cloud Hosting) có thuộc tính ephemeral filesystem (như Render hoặc Railway), bạn phải cấu hình đĩa cứng lưu trữ lâu dài (Persistent Volume) để tránh mất mát dữ liệu khi container khởi động lại hoặc khi deploy phiên bản mới.

### 1. Cấu hình biến môi trường (Environment Variables)

Cài đặt các biến môi trường sau trên trang quản trị Render/Railway của bạn:

| Biến môi trường | Giá trị mẫu / Mô tả |
|-----------------|---------------------|
| `OPENAI_API_KEY` | `sk-proj-...` (OpenAI API key cho RAG & Intent) |
| `JWT_SECRET_KEY` | Một chuỗi hash bảo mật để ký token JWT (Tạo bằng lệnh Python `secrets.token_hex(32)`) |
| `SENDGRID_API_KEY` | `SG....` (Dùng để gửi email follow-up tự động chăm sóc lead) |
| `DATABASE_URL` | `sqlite+aiosqlite:////data/amd_chatbot.db` (Đường dẫn DB trên Volume persistent) |
| `CHROMA_PERSIST_DIR` | `/data/chroma_db` (Thư mục ChromaDB trên Volume persistent) |
| `KNOWLEDGE_BASE_DIR` | `/data/knowledge_base` (Thư mục chứa files upload trên Volume persistent) |
| `JWT_ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `11520` (Mặc định 8 ngày) |
| `SENDER_EMAIL` | `no-reply@yourdomain.com` (Email người gửi đã xác thực trên SendGrid) |

### 2. Thiết lập Persistent Volume (Đĩa lưu trữ lâu dài)

*   **Với Render**:
    1. Vào tab **Disk** trong giao diện dịch vụ Web của bạn.
    2. Chọn **Add Disk**.
    3. Đặt Mount Path là `/data` và dung lượng tối thiểu `1 GB`.
*   **Với Railway**:
    1. Chọn Service, vào phần **Settings** -> **Volumes** -> **Mount Volume**.
    2. Nhập Mount Path là `/data`.
    3. Kiểm tra biến môi trường để chắc chắn các biến đường dẫn (`DATABASE_URL`, `CHROMA_PERSIST_DIR`, `KNOWLEDGE_BASE_DIR`) đã trỏ đúng vào thư mục `/data`.

### 3. Khởi chạy bằng Dockerfile

Codebase đã có sẵn `Dockerfile` hỗ trợ build đa lớp tối ưu dung lượng và chạy tự động server Uvicorn tại cổng `8000`. Lệnh khởi chạy mặc định của container:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Lead Status Flow

```
NEW → CONTACTED → CONSULTING → QUOTED → NEGOTIATING → WON / LOST / COLD
```

Khi trạng thái lead thay đổi → scheduler tự động lập lịch hoặc hủy bỏ các tác vụ follow-up tương ứng theo rules đã cấu hình.

---

## Sync với Intern B

- **API contract**: Xem `docs/api_contract.yaml`
- **Sổ tay vận hành Admin**: Xem `docs/user_guide_admin.md`
- **Tuần 1**: Pair programming, thống nhất schemas.
- **Tuần 2+**: Intern B gọi API từ Frontend qua `http://localhost:8000`.
- **CORS**: Cấu hình CORS hiện tại cho phép truy cập từ origin `http://localhost:5173` (Vite dev server).

