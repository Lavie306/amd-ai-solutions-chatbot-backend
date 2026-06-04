"""
/api/documents — Upload, list, delete, re-index knowledge base files.
"""
from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import require_admin
from app.db.session import get_db
from app.models.models import Document
from app.rag.pipeline import delete_document_chunks, ingest_document
from app.schemas.schemas import DocumentOut

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/documents", tags=["Knowledge Base"])

UPLOAD_DIR = Path("./data/knowledge_base")
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
) -> list[DocumentOut]:
    result = await db.execute(select(Document).order_by(Document.uploaded_at.desc()))
    return result.scalars().all()


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
) -> DocumentOut:
    raw_name = file.filename or ""
    suffix = Path(raw_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Chỉ chấp nhận: {', '.join(ALLOWED_EXTENSIONS)}")

    safe_name = re.sub(r"[^\w.\-]", "_", Path(raw_name).name)
    if safe_name != raw_name:
        logger.warning("Sanitized filename: '%s' → '%s'", raw_name, safe_name)

    # Lưu file
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / safe_name
    content = await file.read()
    file_path.write_bytes(content)

    # Tạo record DB với status indexing
    doc = Document(filename=safe_name, status="indexing")
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Chạy ingest trong background
    asyncio.create_task(_ingest_background(doc.id, file_path, db))

    return doc


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
) -> None:
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    # Xóa chunks trong ChromaDB
    delete_document_chunks(doc_id)

    # Xóa file vật lý
    file_path = UPLOAD_DIR / doc.filename
    if file_path.exists():
        file_path.unlink()

    await db.delete(doc)
    await db.commit()


@router.post("/{doc_id}/reindex", response_model=DocumentOut)
async def reindex_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin),
) -> DocumentOut:
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    # Xóa chunks cũ
    delete_document_chunks(doc_id)

    doc.status = "indexing"
    doc.chunk_count = 0
    await db.commit()

    file_path = UPLOAD_DIR / doc.filename
    asyncio.create_task(_ingest_background(doc_id, file_path, db))

    await db.refresh(doc)
    return doc


async def _ingest_background(doc_id: int, file_path: Path, db: AsyncSession) -> None:
    """Chạy embedding trong background, cập nhật status."""
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import select

    async with AsyncSessionLocal() as bg_db:
        result = await bg_db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            return
        try:
            loop = asyncio.get_event_loop()
            chunk_count = await loop.run_in_executor(None, ingest_document, file_path, doc_id)
            doc.status = "ready"
            doc.chunk_count = chunk_count
        except Exception as e:
            logger.error(f"Ingest failed for doc {doc_id}: {e}")
            doc.status = "error"
        await bg_db.commit()
