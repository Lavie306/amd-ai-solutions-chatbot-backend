"""
Vietnamese NLP utilities + Hallucination Guard (Grounding Check).

Port và adapt từ healthcare-system-backend/app/ai_core/rag/relevance.py
Bỏ phần medical-specific, giữ lại:
  - normalize_vi()         : chuẩn hóa tiếng Việt (bỏ dấu, clean)
  - important_tokens()     : tokenize + lọc stopwords tiếng Việt
  - answer_is_grounded()   : kiểm tra retrieved chunks có liên quan không
                             → ngăn bot bịa thông tin AMD không có trong KB
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any


# ─────────────────────────────────────────────
# Vietnamese stopwords (general — không domain-specific)
# ─────────────────────────────────────────────
_STOPWORDS_VI = {
    "la", "là", "gi", "gì", "co", "có", "cua", "của", "ve", "về",
    "toi", "tôi", "ban", "bạn", "can", "cần", "nen", "nên",
    "khong", "không", "the", "thế", "nhu", "như", "khi", "nao", "nào",
    "dieu", "điều", "thong", "tin", "mot", "một", "nhung", "những",
    "va", "và", "hay", "hoac", "hoặc", "neu", "nếu", "thi", "thì",
    "voi", "với", "cac", "các", "cho", "de", "để", "ma", "mà",
    "trong", "ngoai", "ngoài", "theo", "boi", "bởi", "do", "đó",
    "day", "đây", "kia", "o", "ở", "tren", "trên", "duoi", "dưới",
}


def normalize_vi(text: str) -> str:
    """
    Chuẩn hóa text tiếng Việt:
    1. NFD decompose → bỏ dấu
    2. lowercase
    3. chỉ giữ a-z, 0-9
    4. collapse whitespace

    Ví dụ: "Giá làm Chatbot?" → "gia lam chatbot"
    """
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "D").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def important_tokens(text: str) -> set[str]:
    """
    Trả về tập token quan trọng (đã normalize, lọc stopwords, min 2 ký tự).
    """
    return {
        token
        for token in normalize_vi(text).split()
        if len(token) >= 2 and token not in _STOPWORDS_VI
    }


# ─────────────────────────────────────────────
# Grounding / Hallucination Guard
# ─────────────────────────────────────────────

def answer_is_grounded(query: str, retrieved_chunks: list[dict[str, Any]]) -> bool:
    """
    Kiểm tra xem retrieved chunks có liên quan đến câu hỏi không.

    Trả về True  → có ít nhất 1 chunk overlap đủ mạnh → LLM được phép trả lời.
    Trả về False → không có chunk liên quan → bot nên từ chối / redirect.

    Logic:
      - Lấy important_tokens của query
      - Với mỗi chunk: tính overlap với (content + metadata.filename)
      - Nếu overlap >= 2 rare token (len >= 4) → grounded

    Ví dụ:
      Query   : "giá làm chatbot CSKH bao nhiêu"
      Chunk   : "...AMD cung cấp giải pháp chatbot CSKH cho doanh nghiệp..."
      Overlap : {"chatbot", "cskh"} → grounded = True

      Query   : "bệnh tiểu đường điều trị thế nào"  (ngoài domain AMD)
      Chunks  : [chunks về AI, chatbot, app mobile...]
      Overlap : {} → grounded = False → bot redirect
    """
    q_tokens = important_tokens(query)
    if not q_tokens:
        # Query quá ngắn/rỗng → cho phép trả lời
        return True

    for chunk in retrieved_chunks:
        content = chunk.get("content", "")
        filename = chunk.get("metadata", {}).get("filename", "") if isinstance(chunk.get("metadata"), dict) else ""
        combined_tokens = important_tokens(f"{content} {filename}")

        # Token quan trọng: len >= 4, không phải stopword
        rare_hits = {
            t for t in (q_tokens & combined_tokens)
            if len(t) >= 4
        }
        if len(rare_hits) >= 2:
            return True

        # Signal yếu hơn: overlap >= 3 token bất kỳ
        if len(q_tokens & combined_tokens) >= 3:
            return True

    return False


def build_not_grounded_reply(query: str, handoff_contact: str = "") -> str:
    """
    Câu trả lời mặc định khi không tìm được thông tin liên quan trong KB.
    Bot dẫn khách sang liên hệ trực tiếp thay vì bịa.
    """
    contact_part = f" hoặc liên hệ {handoff_contact}" if handoff_contact else ""
    return (
        f"Xin lỗi, tôi chưa có đủ thông tin để trả lời chính xác câu hỏi này. "
        f"Để được tư vấn cụ thể, anh/chị có thể để lại thông tin"
        f"{contact_part} để team AMD hỗ trợ trực tiếp nhé! 😊"
    )
