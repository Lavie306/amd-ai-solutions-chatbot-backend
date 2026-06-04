"""
Chat Agent — Điều phối toàn bộ luồng hội thoại:
  1. RAG: trả lời FAQ từ knowledge base
     - HyDE query expansion (port từ healthcare)
     - Grounding check (port từ healthcare) — ngăn bot bịa
  2. Intent Detection: phát hiện ý định lead tiềm năng
     - OpenAI classification (primary)
     - Keyword/regex fallback khi OpenAI unavailable
  3. Lead Collection State Machine: IDLE → COLLECTING → COMPLETE
  4. Handoff message khi lead complete
"""
from __future__ import annotations

import logging
import re
from enum import Enum
from typing import Any

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.rag.pipeline import query_knowledge_base
from app.rag.relevance import answer_is_grounded, build_not_grounded_reply

logger = logging.getLogger(__name__)
settings = get_settings()

client = AsyncOpenAI(api_key=settings.openai_api_key)


# ─────────────────────────────────────────────
# Lead Collection State Machine
# ─────────────────────────────────────────────
class LeadState(str, Enum):
    IDLE = "IDLE"
    COLLECTING = "COLLECTING"
    COMPLETE = "COMPLETE"


# ─────────────────────────────────────────────
# Intent Detection — Keyword/Regex Fallback
# ─────────────────────────────────────────────
INTENT_KEYWORD_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'(giá|chi phí|ngân sách|báo giá|tốn bao nhiêu|mất bao nhiêu|bao nhiêu tiền|budget|cost|pricing|quote)', re.IGNORECASE), "ask_price"),
    (re.compile(r'(muốn làm|xây dựng|cần tư vấn giải pháp|tích hợp|cần làm|muốn xây|cần xây|làm app|làm web|automation|cần dự án)', re.IGNORECASE), "want_project"),
    (re.compile(r'(tư vấn viên|cho tôi gặp|demo|đặt lịch|gặp trực tiếp|chuyên gia|liên hệ tư vấn|cuộc hẹn|muốn gặp|xin demo|tư vấn cho tôi)', re.IGNORECASE), "request_consult"),
]


def detect_intent_keyword(user_message: str) -> str | None:
    """Fallback keyword/regex intent detection khi OpenAI unavailable."""
    for pattern, intent in INTENT_KEYWORD_PATTERNS:
        if pattern.search(user_message):
            return intent
    return None


# ─────────────────────────────────────────────
# Intent Detection — Primary (OpenAI + Fallback)
# ─────────────────────────────────────────────
INTENT_SYSTEM_PROMPT = """Bạn là hệ thống phân loại intent cho chatbot AMD AI Solutions.
Phân tích câu hỏi của khách và trả về 1 trong 4 intent sau (chỉ trả về tên intent, không giải thích):

- ask_price: khách hỏi về giá, chi phí, budget
- want_project: khách muốn làm dự án AI, app, chatbot
- request_consult: khách muốn gặp tư vấn viên, xin demo, đặt lịch
- general_faq: hỏi thông tin chung, không có ý định mua

Chỉ trả về đúng 1 từ: ask_price | want_project | request_consult | general_faq"""


async def detect_intent(user_message: str) -> str:
    """Phân loại intent: ưu tiên OpenAI, fallback keyword/regex."""
    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=20,
            temperature=0,
        )
        intent = response.choices[0].message.content.strip().lower()
        if intent in ("ask_price", "want_project", "request_consult", "general_faq"):
            return intent
    except Exception as e:
        logger.warning(f"OpenAI intent detection failed, falling back to keyword: {e}")

    keyword_intent = detect_intent_keyword(user_message)
    return keyword_intent if keyword_intent else "general_faq"


# ─────────────────────────────────────────────
# RAG Answer (với HyDE + Grounding check)
# ─────────────────────────────────────────────
async def get_rag_answer(
    user_message: str,
    chat_history: list[dict],
    bot_name: str = "AMD Assistant",
    handoff_contact: str = "",
) -> str:
    """
    Trả lời FAQ dựa trên knowledge base.

    Pipeline (ported từ healthcare-system-backend):
      1. HyDE: mở rộng query → tìm chunk liên quan hơn
      2. Grounding check: nếu không có chunk phù hợp → bot từ chối / redirect
         thay vì bịa thông tin AMD
      3. LLM tổng hợp trả lời từ chunks đã retrieve
    """
    # ── Bước 1: Retrieve với HyDE ──────────────────────────────
    chunks = await query_knowledge_base(
        query=user_message,
        k=4,
        use_hyde=True,
        openai_client=client,
    )

    # ── Bước 2: Grounding check ────────────────────────────────
    # Port từ healthcare relevance.py — ngăn bot bịa thông tin
    if chunks and not answer_is_grounded(user_message, chunks):
        logger.info(f"RAG not grounded for query: {user_message[:60]}")
        return build_not_grounded_reply(user_message, handoff_contact)

    context = "\n\n---\n\n".join(c["content"] for c in chunks) if chunks else ""

    # ── Bước 3: LLM tổng hợp câu trả lời ─────────────────────
    if not context:
        return build_not_grounded_reply(user_message, handoff_contact)

    system_prompt = f"""Bạn là {bot_name}, trợ lý tư vấn của AMD AI Solutions.
Trả lời dựa trên thông tin bên dưới. Nếu không có thông tin, hãy thừa nhận và gợi ý khách liên hệ trực tiếp.
Trả lời ngắn gọn, thân thiện, bằng tiếng Việt. Không được bịa thông tin ngoài context.

=== Thông tin AMD ===
{context}
==================="""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(chat_history[-8:])  # Giữ 8 tin nhắn gần nhất
    messages.append({"role": "user", "content": user_message})

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        max_tokens=500,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


# ─────────────────────────────────────────────
# Lead Collection
# ─────────────────────────────────────────────
async def collect_lead_turn(
    user_message: str,
    chat_history: list[dict],
    collected_fields: dict[str, Any],
    available_fields: list[dict],
    bot_name: str = "AMD Assistant",
) -> tuple[str, dict[str, Any], LeadState]:
    """
    Một lượt hỏi thu thập thông tin lead.
    Trả về: (reply, updated_fields, new_state)
    """
    fields_desc = "\n".join(
        f"- {f['key']}: {f['label']} ({'bắt buộc' if f.get('required') else 'linh hoạt'})"
        for f in available_fields
        if f.get("enabled", True)
    )

    collected_desc = "\n".join(f"- {k}: {v}" for k, v in collected_fields.items())

    system_prompt = f"""Bạn là {bot_name}, đang thu thập thông tin để team AMD liên hệ tư vấn.

Thông tin đã thu thập được:
{collected_desc or "(chưa có)"}

Các trường có thể hỏi thêm:
{fields_desc}

Quy tắc:
1. Luôn ưu tiên lấy "name" và "contact" (SĐT/email) trước.
2. Sau khi có name + contact, chỉ hỏi thêm 2-3 trường phù hợp với ngữ cảnh hội thoại.
3. Hỏi tự nhiên, không liệt kê dạng form.
4. Khi đã đủ thông tin (có name + contact + ít nhất 2 trường khác), trả lời JSON:
   {{"action": "complete", "fields": {{"<key>": "<value>", ...}}, "reply": "<câu cảm ơn handoff>"}}
5. Nếu chưa đủ, trả lời JSON:
   {{"action": "ask", "fields": {{"<key đã extract>": "<value>", ...}}, "reply": "<câu hỏi tiếp theo>"}}

Chỉ trả về JSON thuần, không giải thích thêm."""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(chat_history[-10:])
    messages.append({"role": "user", "content": user_message})

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
        max_tokens=600,
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    import json
    data = json.loads(response.choices[0].message.content)

    # Merge fields mới vào collected
    new_fields = {**collected_fields, **data.get("fields", {})}
    reply = data.get("reply", "")

    if data.get("action") == "complete":
        return reply, new_fields, LeadState.COMPLETE
    return reply, new_fields, LeadState.COLLECTING


# ─────────────────────────────────────────────
# Main Chat Handler (entry point)
# ─────────────────────────────────────────────
async def handle_chat(
    session_id: str,
    user_message: str,
    chat_history: list[dict],
    lead_state: str,
    collected_fields: dict[str, Any],
    available_fields: list[dict],
    settings_dict: dict[str, Any],
) -> dict[str, Any]:
    """
    Entry point được gọi từ API router.

    Trả về dict:
      - reply: str
      - intent: str | None
      - lead_state: str
      - collected_fields: dict
    """
    bot_name = settings_dict.get("bot_name", "AMD Assistant")
    current_state = LeadState(lead_state)

    # Nếu đang trong flow collecting, tiếp tục collect
    if current_state == LeadState.COLLECTING:
        reply, new_fields, new_state = await collect_lead_turn(
            user_message, chat_history, collected_fields, available_fields, bot_name
        )
        return {
            "reply": reply,
            "intent": None,
            "lead_state": new_state.value,
            "collected_fields": new_fields,
        }

    # IDLE: detect intent trước
    intent = await detect_intent(user_message)
    logger.info(f"[{session_id}] Intent detected: {intent}")

    lead_intents = {"ask_price", "want_project", "request_consult"}

    if intent in lead_intents and current_state == LeadState.IDLE:
        # Bắt đầu flow collect lead
        reply, new_fields, new_state = await collect_lead_turn(
            user_message, chat_history, collected_fields, available_fields, bot_name
        )
        return {
            "reply": reply,
            "intent": intent,
            "lead_state": new_state.value,
            "collected_fields": new_fields,
        }

    # general_faq hoặc COMPLETE → RAG answer (với HyDE + grounding check)
    handoff_contact = settings_dict.get("chatbot.zalo_number", "")
    reply = await get_rag_answer(user_message, chat_history, bot_name, handoff_contact)
    return {
        "reply": reply,
        "intent": intent,
        "lead_state": current_state.value,
        "collected_fields": collected_fields,
    }
