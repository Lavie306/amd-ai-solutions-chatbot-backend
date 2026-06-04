"""
Integration tests for the Documents (Knowledge Base) API.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from pathlib import Path
from unittest.mock import MagicMock

from app.main import app
from app.core.config import get_settings

settings = get_settings()

@pytest.fixture
def admin_headers():
    from app.core.security import create_access_token
    token = create_access_token(settings.admin_email)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def temp_upload_dir(tmp_path, monkeypatch):
    """Mock upload directory to point to a temp path."""
    import app.api.routes.documents as docs_route
    monkeypatch.setattr(docs_route, "UPLOAD_DIR", tmp_path)
    return tmp_path

@pytest.fixture
def mock_ingest(monkeypatch):
    """Mock the background ingest function to avoid real embeddings call."""
    import app.api.routes.documents as docs_route
    mock = MagicMock()
    # Mock _ingest_background
    async def dummy_ingest(doc_id, file_path, db):
        pass
    monkeypatch.setattr(docs_route, "_ingest_background", dummy_ingest)
    return mock

@pytest.fixture
def mock_pipeline(monkeypatch):
    """Mock pipeline functions."""
    import app.api.routes.documents as docs_route
    mock_delete = MagicMock()
    monkeypatch.setattr(docs_route, "delete_document_chunks", mock_delete)
    return mock_delete

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest.mark.asyncio
async def test_list_documents_unauthorized(client: AsyncClient) -> None:
    response = await client.get("/api/documents")
    # Should require bearer auth
    assert response.status_code == 403 or response.status_code == 401

@pytest.mark.asyncio
async def test_list_documents_authorized(client: AsyncClient, admin_headers) -> None:
    response = await client.get("/api/documents", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_upload_document_success(
    client: AsyncClient, admin_headers, temp_upload_dir, mock_ingest
) -> None:
    files = {"file": ("test_doc.txt", b"Hello AMD AI Solutions FAQ info", "text/plain")}
    response = await client.post(
        "/api/documents",
        files=files,
        headers=admin_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "test_doc.txt"
    assert data["status"] == "indexing"
    
    # Check file exists on mock disk
    uploaded_file = temp_upload_dir / "test_doc.txt"
    assert uploaded_file.exists()
    assert uploaded_file.read_bytes() == b"Hello AMD AI Solutions FAQ info"

@pytest.mark.asyncio
async def test_upload_invalid_extension(client: AsyncClient, admin_headers) -> None:
    files = {"file": ("test_image.png", b"fake-png-data", "image/png")}
    response = await client.post(
        "/api/documents",
        files=files,
        headers=admin_headers
    )
    assert response.status_code == 400
    assert "Chỉ chấp nhận" in response.json()["detail"]

@pytest.mark.asyncio
async def test_delete_document_not_found(
    client: AsyncClient, admin_headers, mock_pipeline
) -> None:
    response = await client.delete("/api/documents/999999", headers=admin_headers)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_delete_document_success(
    client: AsyncClient, admin_headers, temp_upload_dir, mock_ingest, mock_pipeline
) -> None:
    # First upload a document to get a valid ID
    files = {"file": ("test_delete.txt", b"to be deleted", "text/plain")}
    up_res = await client.post("/api/documents", files=files, headers=admin_headers)
    doc_id = up_res.json()["id"]

    # Delete it
    del_res = await client.delete(f"/api/documents/{doc_id}", headers=admin_headers)
    assert del_res.status_code == 204

    # Verify document is gone from lists
    list_res = await client.get("/api/documents", headers=admin_headers)
    ids = [d["id"] for d in list_res.json()]
    assert doc_id not in ids

@pytest.mark.asyncio
async def test_reindex_document_success(
    client: AsyncClient, admin_headers, temp_upload_dir, mock_ingest, mock_pipeline
) -> None:
    # Upload first
    files = {"file": ("test_reindex.txt", b"reindex content", "text/plain")}
    up_res = await client.post("/api/documents", files=files, headers=admin_headers)
    doc_id = up_res.json()["id"]

    # Trigger reindex
    re_res = await client.post(f"/api/documents/{doc_id}/reindex", headers=admin_headers)
    assert re_res.status_code == 200
    data = re_res.json()
    assert data["id"] == doc_id
    assert data["status"] == "indexing"
