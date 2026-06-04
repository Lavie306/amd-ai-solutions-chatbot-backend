"""
Keyword Retriever — fallback retriever không cần OpenAI/FAISS.

Port từ healthcare-system-backend/app/ai_core/rag/retriever.py
Adapted for AMD chatbot (loại bỏ dependency vào healthcare config).

Dùng khi:
  - OPENAI_API_KEY chưa có (tuần 1 POC)
  - Smoke test / unit test không muốn tốn tiền API
  - Offline demo
"""
from __future__ import annotations

import math
from typing import Any


class KeywordRetriever:
    """
    Fallback retriever dùng token overlap + length boost.

    Không cần bất kỳ model hay API nào.
    Phù hợp cho dev/test khi chưa có OpenAI key.
    """

    def __init__(self, docs: list[dict[str, Any]], k: int = 4):
        """
        Args:
            docs: list of {"content": str, "metadata": dict, ...}
            k: số chunk trả về tối đa
        """
        self.docs = docs
        self.k = k

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {
            t.strip(".,;:!?()[]{}\"'").lower()
            for t in text.split()
            if len(t.strip()) >= 2
        }

    def invoke(self, query: str) -> list[dict[str, Any]]:
        q_tokens = self._tokens(query)
        scored: list[tuple[float, dict]] = []

        for doc in self.docs:
            text = doc.get("content", "")
            d_tokens = self._tokens(text)
            overlap = len(q_tokens & d_tokens)
            # Length boost nhỏ để tránh ưu tiên chunk quá ngắn
            score = overlap + math.log1p(len(text)) * 0.01
            if overlap > 0:
                scored.append((score, doc))

        if not scored:
            # Không có overlap → trả về k chunk đầu tiên
            return self.docs[: self.k]

        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[: self.k]]
