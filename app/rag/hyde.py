"""
HyDE — Hypothetical Document Embedding.

Port từ healthcare-system-backend/app/ai_core/rag/hyde.py
Adapted cho AMD AI Solutions domain.

Kỹ thuật:
  Thay vì embed câu hỏi gốc "giá chatbot bao nhiêu?" để search vectorstore,
  ta dùng LLM sinh ra một đoạn văn "giả định" như thể đó là câu trả lời:
    → "AMD cung cấp dịch vụ chatbot với chi phí từ... phụ thuộc vào..."
  Rồi embed đoạn văn đó để search.

  Tại sao tốt hơn:
  - Semantic space của "câu trả lời" gần hơn với chunks trong KB
  - Đặc biệt hiệu quả với câu hỏi ngắn, thiếu context ("giá?", "timeline?")

  Trade-off:
  - Tốn thêm 1 LLM call / request (gpt-4o-mini ~$0.00002/call → không đáng kể)
  - Nếu LLM call fail → fallback về query gốc, không crash
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# Prompt cho AMD domain — khác với healthcare (bác sĩ) → tư vấn AI solutions
_HYDE_PROMPT = (
    "Bạn là chuyên gia tư vấn của AMD AI Solutions — công ty cung cấp giải pháp AI "
    "như chatbot, app mobile AI, hệ thống automation cho doanh nghiệp.\n\n"
    "Viết một đoạn văn ngắn (2-3 câu) mô tả thông tin liên quan đến câu hỏi sau, "
    "như thể đây là trích đoạn từ brochure hoặc tài liệu giới thiệu dịch vụ AMD. "
    "Không giải thích thêm, không hỏi lại.\n\n"
    "Câu hỏi: {query}\n"
    "Đoạn văn mô tả dịch vụ AMD:"
)


async def expand_query_hyde(
    query: str,
    client: "AsyncOpenAI",
    model: str = "gpt-4o-mini",
    use_hyde: bool = True,
) -> str:
    """
    Mở rộng query bằng HyDE trước khi search vectorstore.

    Args:
        query    : câu hỏi gốc của khách
        client   : AsyncOpenAI instance
        model    : LLM dùng để generate hypothetical doc
        use_hyde : False → bypass, trả về query gốc luôn

    Returns:
        hypothetical document string (dùng để embed+search)
        hoặc query gốc nếu HyDE fail / use_hyde=False
    """
    if not use_hyde:
        return query

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": _HYDE_PROMPT.format(query=query),
                }
            ],
            max_tokens=200,
            temperature=0.3,
        )
        hypothetical = response.choices[0].message.content.strip()

        if len(hypothetical) < 20:
            logger.debug("HyDE output quá ngắn, fallback về query gốc")
            return query

        logger.debug("HyDE expanded: %s → %s", query[:60], hypothetical[:80])
        return hypothetical

    except Exception as exc:
        logger.warning("HyDE failed, fallback về query gốc: %s", exc)
        return query
