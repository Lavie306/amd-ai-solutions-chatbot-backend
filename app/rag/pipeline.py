"""
RAG Pipeline — Ingest, chunking, embedding, query.

Flow:
  upload file → chunk → embed → lưu vào ChromaDB → query khi chat

Đã tích hợp từ healthcare-system-backend:
  - KeywordRetriever  : fallback offline khi không có OpenAI key
  - HyDE              : mở rộng query trước khi search → cải thiện recall
  - answer_is_grounded: kiểm tra chunk liên quan trước khi cho LLM trả lời
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ─────────────────────────────────────────────
# ChromaDB + OpenAI Embeddings (primary)
# ─────────────────────────────────────────────

def _get_vector_store():
    """Khởi tạo ChromaDB với OpenAI embeddings."""
    from langchain_chroma import Chroma
    from langchain_openai import OpenAIEmbeddings

    embeddings = OpenAIEmbeddings(
        model=settings.openai_embedding_model,
        openai_api_key=settings.openai_api_key,
    )
    return Chroma(
        collection_name=settings.chroma_collection_name,
        embedding_function=embeddings,
        persist_directory=settings.chroma_persist_dir,
    )


def _is_openai_available() -> bool:
    """Kiểm tra xem OpenAI API key có được cấu hình không."""
    return bool(settings.openai_api_key and not settings.openai_api_key.startswith("sk-..."))


# ─────────────────────────────────────────────
# File Loaders
# ─────────────────────────────────────────────

def _load_file(file_path: Path) -> list[Document]:
    """Load file theo extension."""
    from langchain_community.document_loaders import (
        PyPDFLoader,
        TextLoader,
        UnstructuredWordDocumentLoader,
    )

    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        loader = PyPDFLoader(str(file_path))
    elif suffix in (".docx", ".doc"):
        loader = UnstructuredWordDocumentLoader(str(file_path))
    elif suffix in (".txt", ".md"):
        loader = TextLoader(str(file_path), encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {suffix}")
    return loader.load()


# ─────────────────────────────────────────────
# Ingest
# ─────────────────────────────────────────────

def ingest_document(file_path: Path, document_id: int) -> int:
    """
    Ingest một file vào ChromaDB.
    Trả về số chunk đã tạo.
    """
    logger.info(f"Ingesting document: {file_path.name} (id={document_id})")

    raw_docs = _load_file(file_path)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n\n", "\n", "。", ".", " ", ""],
    )
    chunks = splitter.split_documents(raw_docs)

    for i, chunk in enumerate(chunks):
        chunk.metadata.update(
            {
                "document_id": document_id,
                "filename": file_path.name,
                "chunk_index": i,
            }
        )

    vector_store = _get_vector_store()
    vector_store.add_documents(chunks)

    logger.info(f"Ingested {len(chunks)} chunks for document {file_path.name}")
    return len(chunks)


def delete_document_chunks(document_id: int) -> None:
    """Xóa toàn bộ chunks của một document khỏi ChromaDB."""
    vector_store = _get_vector_store()
    vector_store._collection.delete(where={"document_id": document_id})
    logger.info(f"Deleted chunks for document_id={document_id}")


# ─────────────────────────────────────────────
# Corpus fingerprint (từ healthcare retriever.py)
# Dùng để phát hiện KB có thay đổi không
# ─────────────────────────────────────────────

def fingerprint_corpus(document_ids: list[int], chunk_counts: list[int]) -> str:
    """
    SHA256 hash trạng thái Knowledge Base.
    Dùng để detect khi nào ChromaDB collection bị stale
    (admin upload/xóa doc mà không re-embed).
    """
    h = hashlib.sha256()
    for doc_id, cnt in sorted(zip(document_ids, chunk_counts)):
        h.update(f"{doc_id}:{cnt}\n".encode())
    return h.hexdigest()


# ─────────────────────────────────────────────
# Query — ChromaDB với HyDE + Grounding check
# ─────────────────────────────────────────────

async def query_knowledge_base(
    query: str,
    k: int = 4,
    use_hyde: bool = True,
    openai_client: Any | None = None,
) -> list[dict[str, Any]]:
    """
    Tìm kiếm trong ChromaDB với HyDE query expansion.

    Flow:
      1. [HyDE] Nếu openai_client có và use_hyde=True:
           query → LLM generate hypothetical doc → embed hypothetical
         Nếu không: embed query gốc
      2. ChromaDB similarity search với embedding đó
      3. Trả về list chunks với content + metadata + score

    Args:
        query         : câu hỏi của khách
        k             : số chunk trả về
        use_hyde      : có dùng HyDE không (default True)
        openai_client : AsyncOpenAI instance (cần cho HyDE)

    Returns:
        list of {"content": str, "metadata": dict, "score": float}
    """
    # ── Bước 1: HyDE query expansion ──────────────────────────
    search_query = query
    if use_hyde and openai_client is not None and _is_openai_available():
        try:
            from app.rag.hyde import expand_query_hyde
            search_query = await expand_query_hyde(
                query=query,
                client=openai_client,
                model=settings.openai_model,
                use_hyde=True,
            )
        except Exception as e:
            logger.warning(f"HyDE expansion skipped: {e}")
            search_query = query

    # ── Bước 2: ChromaDB similarity search ────────────────────
    if not _is_openai_available():
        # Fallback: dùng KeywordRetriever (offline)
        logger.warning("OpenAI key chưa có — dùng KeywordRetriever fallback")
        return _keyword_query_fallback(query=query, k=k)

    try:
        vector_store = _get_vector_store()
        results = vector_store.similarity_search_with_score(search_query, k=k)
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score),
            }
            for doc, score in results
        ]
    except Exception as e:
        logger.error(f"ChromaDB query failed: {e} — fallback to keyword retriever")
        return _keyword_query_fallback(query=query, k=k)


def _keyword_query_fallback(query: str, k: int = 4) -> list[dict[str, Any]]:
    """
    Dùng KeywordRetriever khi ChromaDB không khả dụng.
    Đọc chunks từ disk nếu có, hoặc trả về list rỗng.

    Port từ healthcare KeywordRetriever — hoạt động hoàn toàn offline.
    """
    from app.rag.keyword_retriever import KeywordRetriever

    # Thử load documents từ file knowledge_base đã có
    kb_dir = Path("./data/knowledge_base")
    docs: list[dict] = []
    if kb_dir.exists():
        for txt_file in kb_dir.glob("*.txt"):
            try:
                text = txt_file.read_text(encoding="utf-8")
                # Chunk đơn giản theo đoạn
                for i, para in enumerate(text.split("\n\n")):
                    para = para.strip()
                    if len(para) > 20:
                        docs.append({
                            "content": para,
                            "metadata": {"filename": txt_file.name, "chunk_index": i},
                        })
            except Exception:
                pass

    if not docs:
        logger.warning("KeywordRetriever: không có docs nào để search")
        return []

    retriever = KeywordRetriever(docs=docs, k=k)
    return retriever.invoke(query)


# ─────────────────────────────────────────────
# Sync wrapper (cho code gọi từ executor/thread)
# ─────────────────────────────────────────────

def query_knowledge_base_sync(query: str, k: int = 4) -> list[dict[str, Any]]:
    """
    Sync version của query_knowledge_base (không có HyDE).
    Dùng trong background thread (executor) hoặc script.
    """
    if not _is_openai_available():
        return _keyword_query_fallback(query=query, k=k)

    vector_store = _get_vector_store()
    results = vector_store.similarity_search_with_score(query, k=k)
    return [
        {
            "content": doc.page_content,
            "metadata": doc.metadata,
            "score": float(score),
        }
        for doc, score in results
    ]
